from flask import Flask, render_template, request, send_file
import os
from master_orchestrator import run

app = Flask(__name__, template_folder=".")

# 🔐 KEEP PASSWORD HERE (NOT IN UI)
SECURITY_PASSWORD = os.getenv("ROAD_API_PASSWORD")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        road_id = request.form.get("road_id")
        road_type = request.form.get("road_type")

        if not road_id or not road_type:
            return render_template("index.html", error="All fields required")

        try:
            result = run(
                road_ids=int(road_id),
                road_type=road_type,
                security_password=SECURITY_PASSWORD,
                run_stages=["fetch", "process", "excel"]
            )

            excel_info = result["generated_excels"][0]
            file_path = excel_info["file_path"]

            return send_file(file_path, as_attachment=True)

        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
