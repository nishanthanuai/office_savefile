from flask import Flask, render_template, request, jsonify, Response
import subprocess
import threading
import queue
import os
from datetime import datetime
import json
from flask import send_file
from master_runner import run_pipeline as execute_pipeline

app = Flask(__name__)

# Store active processes
active_processes = {}
log_queues = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run-pipeline', methods=['POST'])
def run_pipeline():
    data = request.json
    survey_id = data.get('survey_id', '').strip()

    if not survey_id.isdigit():
        return jsonify({'error': 'Invalid Survey ID. Must be numeric.'}), 400

    # Create a unique process ID
    process_id = f"{survey_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create a queue for this process
    log_queues[process_id] = queue.Queue()

    # Start the pipeline in a separate thread
    thread = threading.Thread(
        target=run_pipeline_process,
        args=(survey_id, process_id)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'process_id': process_id, 'status': 'started'})


@app.route('/download/<process_id>')
def download_file(process_id):

    result = active_processes.get(process_id)

    if not result:
        return jsonify({'error': 'File not ready'}), 404

    # You need to store excel path somewhere
    excel_path = result.get("excel_path")

    if not excel_path or not os.path.exists(excel_path):
        return jsonify({'error': 'File not found'}), 404

    return send_file(excel_path, as_attachment=True)


def run_pipeline_process(survey_id, process_id):
    """Run master_runner pipeline directly and stream logs via queue"""

    try:
        log_queue = log_queues[process_id]

        # Custom logger handler to capture logs
        import logging

        class QueueHandler(logging.Handler):
            def emit(self, record):
                log_entry = self.format(record)
                log_queue.put(log_entry)

        # Attach handler to MASTER_RUNNER logger
        queue_handler = QueueHandler()
        queue_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(message)s")
        )

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(queue_handler)

        # Run pipeline
        result = execute_pipeline(int(survey_id))

        # Remove handler after execution
        root_logger.removeHandler(queue_handler)

        if result:
            active_processes[process_id] = {
                "excel_path": result.get("excel_path"),
                "api_counts": result.get("api_counts"),
                "excel_counts": result.get("excel_counts"),
                "validation_status": result.get("validation_status")
            }

            log_queue.put("__COMPLETED__")

        else:
            log_queue.put("__ERROR__Pipeline returned no result")

    except Exception as e:
        log_queue.put(f"__ERROR__{str(e)}")


@app.route('/stream-logs/<process_id>')
def stream_logs(process_id):
    """Stream logs to the client using Server-Sent Events"""
    def generate():
        if process_id not in log_queues:
            yield f"data: {json.dumps({'error': 'Process not found'})}\n\n"
            return

        log_queue = log_queues[process_id]

        while True:
            try:
                log_line = log_queue.get(timeout=30)

                if log_line.startswith("__COMPLETED__"):

                    result = active_processes.get(process_id, {})

                    yield f"data: {json.dumps({
                        'status': 'completed',
                        'validation_status': result.get('validation_status'),
                        'api_counts': result.get('api_counts'),
                        'excel_counts': result.get('excel_counts')
                    })}\n\n"
                    break

                else:
                    yield f"data: {json.dumps({'log': log_line})}\n\n"

            except queue.Empty:
                yield f"data: {json.dumps({'keepalive': True})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
