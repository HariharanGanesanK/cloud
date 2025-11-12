from config import OTP_NOTIFY_BUSINESS, OTP_NOTIFY_IT

def get_roles_for_otp(branch_name: str):
    """
    Returns a role mapping dict for business + IT roles
    with branch restrictions handled.
    """
    business_roles = OTP_NOTIFY_BUSINESS["roles"]
    it_roles = OTP_NOTIFY_IT["roles"]

    return {
        "business": {
            "roles": business_roles,
            "branch": None
        },
        "it": {
            "roles": it_roles,
            "branch_restricted": OTP_NOTIFY_IT["branch_restricted"],
            "branch": branch_name if OTP_NOTIFY_IT["branch_restricted"] else None
        }
    }
