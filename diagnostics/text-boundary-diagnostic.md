# Temporary text-boundary diagnostic patch (not applied)

Target branch: analysis/searchguard-2026-10-09-multi-target-fix
Target source: guard0826.py
Target source SHA: 16de9fd439820398789fa1fcb772e1262ad491fc

This file only documents a proposed diagnostic. It does not change the live Open WebUI Function.

At inlet(), immediately after original_user_text is extracted, insert:

    diag_has_replacement = "\ufffd" in original_user_text
    diag_has_site = "サイト" in original_user_text
    print(
        "[Bonsai2 Web Search Guard] TEXT_BOUNDARY "
        f"stage=inlet msg={message_id or 'none'} "
        f"chars={len(original_user_text)} "
        f"has_replacement={diag_has_replacement} "
        f"has_site={diag_has_site}"
    )

In _request_impl(), after user_text has been resolved and before its subsequent if user_text: block, insert:

    diag_has_replacement = "\ufffd" in user_text
    diag_has_site = "サイト" in user_text
    print(
        "[Bonsai2 Web Search Guard] TEXT_BOUNDARY "
        f"stage=request msg={state_key} "
        f"chars={len(user_text)} "
        f"has_replacement={diag_has_replacement} "
        f"has_site={diag_has_site}"
    )

The diagnostic logs only text length and boolean flags, not the prompt itself. Review exact insertion points before applying. Do not register or run this patch until reviewed.
