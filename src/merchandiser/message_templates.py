"""Message templates for B-side and M-side AI Merchandiser communications."""

B_MILESTONE_REVIEW = (
    "Milestone confirmation required:\n"
    "The supplier uploaded {media_count} photo(s) for the {milestone_type} stage.\n"
    "Reply:\nA. Confirm\nB. Request more photos\nC. Raise issue"
)

B_LOGISTICS_UPDATE = (
    "Logistics update:\n"
    "Tracking number {tracking_number} ({carrier_name}) — status: {normalized_status}."
)

B_DELIVERY_SIGNOFF = (
    "The shipment ({tracking_number}) has been marked as delivered. "
    "Please confirm receipt:\n"
    "A. Confirm received\nB. Not received\nC. Received with issue"
)

B_EXCEPTION_OPTIONS = (
    "Exception: {exception_type}.\n"
    "Available options:\n{options_text}"
)

M_PROGRESS_CHECK = (
    "老板，订单已确认。{stage}阶段需要更新进度。请回复：\n"
    "A. 已完成\nB. 进行中\nC. 有问题，需要说明"
)

M_MEDIA_UPLOAD = (
    "请上传{milestone_type}阶段照片：{media_desc}。拍清楚一点，方便 buyer 确认。"
)

M_LOGISTICS_HANDOVER = (
    "订单已到物流交接阶段。请回复物流公司、运单号，并上传面单照片。\n"
    "例如：已发顺丰，单号 SF123456789，今天下午发出。"
)

M_MATERIAL_DELAY_RESPONSE = (
    "请确认是否采用备用布料方案，或继续等待原布料。若影响交期，请说明新的预计完成时间。"
)


def render(template: str, **kwargs) -> str:
    return template.format(**kwargs)
