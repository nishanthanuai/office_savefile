import streamlit as st
import logging
from master_runner import run_pipeline
import os

# -----------------------------
# STREAMLIT PAGE
# -----------------------------
st.set_page_config(
    page_title="Road Athena Final Excel Pipeline",
    layout="wide"
)

st.title("🚦 Road Processing Pipeline")
st.write("Enter Survey ID to generate Final Excel and validate dashboard counts.")

survey_id = st.text_input("Survey ID")

run_btn = st.button("Run Pipeline")

log_box = st.empty()


# -----------------------------
# LOG CAPTURE HANDLER
# -----------------------------
class StreamlitLogHandler(logging.Handler):

    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.logs = []

    def emit(self, record):

        msg = self.format(record)
        self.logs.append(msg)

        self.placeholder.code("\n".join(self.logs))


# -----------------------------
# HELPER FUNCTION FOR TOTAL
# -----------------------------
def safe_sum(counts):

    total = 0

    for v in counts.values():

        if isinstance(v, int):
            total += v

        elif isinstance(v, dict):
            total += v.get("count", 0)

    return total


# -----------------------------
# RUN PIPELINE
# -----------------------------
if run_btn:

    if not survey_id.isdigit():
        st.error("Survey ID must be numeric")
        st.stop()

    st.info("Starting pipeline...")

    handler = StreamlitLogHandler(log_box)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))

    logging.getLogger().addHandler(handler)

    result = run_pipeline(int(survey_id))

    logging.getLogger().removeHandler(handler)

    if not result:

        st.error("Pipeline failed")
        st.stop()

    # ----------------------------------
    # SHOW VALIDATION RESULTS
    # ----------------------------------
    st.header("📊 Validation Results")

    api_counts = result["api_counts"]
    excel_counts = result["excel_counts"]
    status = result["validation_status"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dashboard Counts (API)")
        st.json(api_counts)

    with col2:
        st.subheader("Excel Counts")
        st.json(excel_counts)

    # ----------------------------------
    # TOTAL COUNT
    # ----------------------------------
    if api_counts and excel_counts:

        api_total = safe_sum(api_counts)
        excel_total = safe_sum(excel_counts)

        st.write("### Total Counts")

        st.write(f"Dashboard Total : **{api_total}**")
        st.write(f"Excel Total : **{excel_total}**")

    # ----------------------------------
    # FINAL RESULT
    # ----------------------------------
    if status:

        st.success(
            "🎉 Congratulations! Validation successful — Dashboard and Excel counts match."
        )

    else:

        st.error("❌ Validation Failed — Counts mismatch detected.")

    # ----------------------------------
    # FINAL EXCEL DOWNLOAD
    # ----------------------------------
    excel_path = result["excel_path"]

    if excel_path and os.path.exists(excel_path):

        st.success(f"Final Excel Generated: {excel_path}")

        with open(excel_path, "rb") as file:

            st.download_button(
                label="⬇ Download Final Excel",
                data=file,
                file_name=os.path.basename(excel_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
