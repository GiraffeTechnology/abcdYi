"""B-side exception option presentation."""
from src.merchandiser.b_side.b_merchandiser_service import send_b_side_status_update


def present_exception_options(
    project_id: str,
    buyer_actor_id: str,
    exception_type: str,
    proposed_options: list[dict],
) -> dict:
    opts_text = "\n".join(
        f"{chr(65+i)}. {opt.get('description', str(opt))}"
        for i, opt in enumerate(proposed_options)
    )
    msg = f"Exception: {exception_type.replace('_', ' ').title()}.\nAvailable options:\n{opts_text}"
    return send_b_side_status_update(project_id, buyer_actor_id, msg)
