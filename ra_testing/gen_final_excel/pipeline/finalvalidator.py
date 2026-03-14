TARGET_ASSETS = [
    "CHEVRON",
    "CAUTIONARY_WARNING_SIGNS",
    "HAZARD",
    "PROHIBITORY_MANDATORY_SIGNS",
    "INFORMATORY_SIGNS"
]


def run(api_counts, excel_counts, logger):

    logger.info("FINAL VALIDATION STARTED")

    if not api_counts:
        logger.error("Validator API counts missing")
        return False

    if not excel_counts:
        logger.error("Excel counts missing")
        return False

    api_categories = api_counts.get("categories", {})
    excel_categories = excel_counts.get("categories", {})

    validation_passed = True

    logger.info("========== CATEGORY VALIDATION ==========")

    for asset in TARGET_ASSETS:

        api_value = api_categories.get(asset, 0)
        excel_value = excel_categories.get(asset, 0)

        if api_value == excel_value:

            logger.info(
                f"{asset} ✔ MATCH | API={api_value} Excel={excel_value}"
            )

        else:

            logger.error(
                f"{asset} ❌ MISMATCH | API={api_value} Excel={excel_value}"
            )

            validation_passed = False

    logger.info("=========================================")

    # ----------------------------------
    # TOTAL VALIDATION
    # ----------------------------------

    api_total = api_counts.get("total_assets", 0)
    excel_total = excel_counts.get("total_assets", 0)

    if api_total == excel_total:

        logger.info(
            f"TOTAL ✔ MATCH | API={api_total} Excel={excel_total}"
        )

    else:

        logger.error(
            f"TOTAL ❌ MISMATCH | API={api_total} Excel={excel_total}"
        )

        validation_passed = False

    logger.info("=========================================")

    if validation_passed:

        logger.info("🎉 VALIDATION PASSED")

    else:

        logger.error("🚨 VALIDATION FAILED")

    return validation_passed
