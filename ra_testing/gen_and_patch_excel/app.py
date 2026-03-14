import streamlit as st
import os
from master_orchestrator import run_from_survey
from dotenv import load_dotenv

load_dotenv()

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="Road Processing Pipeline", layout="centered")

st.title(" Road Processing Pipeline")
st.markdown("Enter Survey ID to process all roads automatically.")

# -------------------------------
# INPUT
# -------------------------------
survey_id_input = st.text_input("Survey ID")
run_button = st.button("Generate Pipeline")

# -------------------------------
# RUN PIPELINE
# -------------------------------
if not run_button:
    return
if not survey_id_input:
    st.error("Please enter a Survey ID.")
    return
try:
    survey_id = int(survey_id_input)

    # Placeholder for live status updates
    status_placeholder = st.empty()
    progress_list = []  # To show full list of processed roads

    def progress_callback(msg):
        # Keep all previous messages visible
        progress_list.append(msg)
        status_placeholder.text("\n".join(progress_list))

    # Start processing
    status_placeholder.text("Fetching roads...")

    password = os.environ.get("ROAD_API_PASSWORD")
    road_summary = run_from_survey(
        survey_id=survey_id,
        security_password=password,
        run_stages=["fetch", "process", "excel"],
        progress_callback=progress_callback,
    )

    progress_list.append(" Finished processing all roads!")
    status_placeholder.text("\n".join(progress_list))

    st.success("Pipeline Completed Successfully!")

    # -------------------------------
    # AUTO DOWNLOAD EXCELS
    # -------------------------------
    for road_type, roads in road_summary.items():
        generated = roads.get("generated_excels", [])
        for excel_info in generated:
            excel_path = excel_info["file_path"]
            if os.path.exists(excel_path):
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label=f"📥 Download Excel for Road {excel_info['road_id']}",
                        data=f,
                        file_name=os.path.basename(excel_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            else:
                st.warning(
                    f"Excel file for Road {excel_info['road_id']} not found."
                )

    # Optional: Full JSON summary
    with st.expander("View Full Run Summary"):
        st.json(road_summary)

except ValueError:
    st.error("Survey ID must be numeric.")
except Exception as e:
    st.error(f"Pipeline failed: {str(e)}")
