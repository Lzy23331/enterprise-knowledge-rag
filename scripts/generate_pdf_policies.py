import json
from copy import deepcopy
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "data" / "policies_pdf"
PDF_EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "pdf_eval_cases.jsonl"
COMPANY_NAME = "星河智联科技有限公司"
CONFIDENTIALITY = "内部资料"

CN_NUMBERS = {
    0: "零",
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
    10: "十",
    20: "二十",
    30: "三十",
    40: "四十",
    50: "五十",
    60: "六十",
    70: "七十",
    80: "八十",
    90: "九十",
}


def cn_num(value: int) -> str:
    if value <= 10:
        return CN_NUMBERS[value]
    if value < 20:
        return f"十{CN_NUMBERS[value % 10]}"
    tens, ones = divmod(value, 10)
    if ones == 0:
        return CN_NUMBERS[tens * 10]
    return f"{CN_NUMBERS[tens]}十{CN_NUMBERS[ones]}"


def article_title(number: int, text: str) -> str:
    return f"第{cn_num(number)}条 {text}"


def chapter_title(number: int, title: str) -> str:
    return f"第{cn_num(number)}章 {title}"


def clean_output_dir() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for path in PDF_DIR.glob("*.pdf"):
        path.unlink()
    for path in PDF_DIR.glob("*.metadata.json"):
        path.unlink()


def make_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName="STSong-Light", fontSize=22, leading=30, alignment=TA_CENTER, spaceAfter=18),
        "cover_subtitle": ParagraphStyle("cover_subtitle", parent=base["Normal"], fontName="STSong-Light", fontSize=11, leading=18, alignment=TA_CENTER, spaceAfter=5),
        "chapter": ParagraphStyle("chapter", parent=base["Heading1"], fontName="STSong-Light", fontSize=15, leading=22, spaceBefore=12, spaceAfter=8),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="STSong-Light", fontSize=10, leading=16, firstLineIndent=20, alignment=TA_LEFT),
        "body_no_indent": ParagraphStyle("body_no_indent", parent=base["BodyText"], fontName="STSong-Light", fontSize=10, leading=16, alignment=TA_LEFT),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="STSong-Light", fontSize=8.5, leading=13),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontName="STSong-Light", fontSize=8.5, leading=12),
    }


def paragraph(text: str, style_name: str, styles: dict) -> Paragraph:
    return Paragraph(text, styles[style_name])


def table(data: list[list[str]], widths: list[int], styles: dict) -> Table:
    content = [[Paragraph(str(cell), styles["table"]) for cell in row] for row in data]
    t = Table(content, colWidths=[width * mm for width in widths], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2A44")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA4B2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def header_footer(canvas, doc, spec: dict) -> None:
    canvas.saveState()
    canvas.setFont("STSong-Light", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(18 * mm, 287 * mm, COMPANY_NAME)
    canvas.drawCentredString(105 * mm, 287 * mm, spec["title"])
    canvas.drawRightString(192 * mm, 287 * mm, f"{spec['policy_no']} | {spec['version']} | {CONFIDENTIALITY}")
    canvas.line(18 * mm, 284 * mm, 192 * mm, 284 * mm)
    canvas.drawString(18 * mm, 11 * mm, f"归口部门：{spec['owner']}")
    canvas.drawCentredString(105 * mm, 11 * mm, f"密级：{CONFIDENTIALITY}")
    canvas.drawRightString(192 * mm, 11 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def approval_table(spec: dict, styles: dict) -> Table:
    rows = [["环节", "责任角色", "处理要求", "时限"]]
    for item in spec["approval_flow"]:
        rows.append([item["step"], item["role"], item["requirement"], item["sla"]])
    return table(rows, [24, 34, 84, 28], styles)


def revision_table(spec: dict, styles: dict) -> Table:
    rows = [["版本", "发布日期", "修订内容", "审批人"]]
    rows.extend(spec["revision_history"])
    return table(rows, [22, 34, 82, 32], styles)


def appendix_table(spec: dict, styles: dict) -> list:
    story = []
    for index, appendix in enumerate(spec["appendices"], 1):
        story.append(paragraph(f"附件{cn_num(index)} {appendix['title']}", "chapter", styles))
        story.append(table(appendix["rows"], appendix["widths"], styles))
        story.append(Spacer(1, 10))
    return story


def build_formal_story(spec: dict, styles: dict) -> list:
    story = [
        Spacer(1, 30 * mm),
        paragraph(f"{COMPANY_NAME}", "cover_subtitle", styles),
        paragraph(spec["title"], "cover_title", styles),
        paragraph(f"制度编号：{spec['policy_no']}", "cover_subtitle", styles),
        paragraph(f"版本号：{spec['version']}", "cover_subtitle", styles),
        paragraph(f"发布日期：{spec['publish_date']}", "cover_subtitle", styles),
        paragraph(f"生效日期：{spec['effective_date']}", "cover_subtitle", styles),
        paragraph(f"适用范围：{spec['scope']}", "cover_subtitle", styles),
        Spacer(1, 12 * mm),
        table(
            [
                ["字段", "内容"],
                ["制度密级", CONFIDENTIALITY],
                ["归口部门", spec["department"]],
                ["解释权归属", spec["owner"]],
                ["办理系统", spec["system"]],
                ["适用流程", spec["process_type"]],
                ["表单编号", spec["form_id"]],
            ],
            [35, 125],
            styles,
        ),
        PageBreak(),
        paragraph("修订记录", "chapter", styles),
        revision_table(spec, styles),
        Spacer(1, 8),
        paragraph("审批流程", "chapter", styles),
        approval_table(spec, styles),
    ]
    story.append(PageBreak())

    article_no = 1
    for chapter_index, section in enumerate(spec["sections"], 1):
        story.append(paragraph(chapter_title(chapter_index, section["title"]), "chapter", styles))
        for clause in section["clauses"]:
            story.append(paragraph(article_title(article_no, clause), "body", styles))
            story.append(Spacer(1, 3))
            article_no += 1
        if chapter_index in spec.get("page_break_after", []):
            story.append(PageBreak())

    if spec.get("case_notes"):
        story.append(PageBreak())
        story.append(paragraph("典型场景与处理口径", "chapter", styles))
        for index, note in enumerate(spec["case_notes"], 1):
            story.append(paragraph(f"场景{cn_num(index)}：{note}", "body", styles))
            story.append(Spacer(1, 4))

    if spec.get("control_matrix"):
        story.append(PageBreak())
        story.append(paragraph("监督检查矩阵", "chapter", styles))
        story.append(table(spec["control_matrix"], [34, 46, 42, 48], styles))
        story.append(Spacer(1, 8))
        story.append(paragraph("对检查中发现的制度执行偏差，归口部门应明确整改责任人、整改期限和复核方式；涉及高风险事项的，应同步内审或合规部门。", "body", styles))

    story.append(PageBreak())
    story.extend(appendix_table(spec, styles))
    story.extend(
        [
            paragraph("解释权归属", "chapter", styles),
            paragraph(f"本制度由{spec['owner']}负责解释。跨部门争议由流程负责人组织相关部门共同确认，并以系统审批记录和正式制度文本为准。", "body", styles),
        ]
    )
    return story


def metadata_for(spec: dict) -> dict:
    return {
        "doc_id": spec["doc_id"],
        "title": spec["title"],
        "department": spec["department"],
        "process_type": spec["process_type"],
        "risk_level": spec["risk_level"],
        "owner": spec["owner"],
        "system": spec["system"],
        "form_id": spec["form_id"],
        "approval_sla": spec["approval_sla"],
        "version": spec["version"],
        "effective_date": spec["effective_date"],
        "published_at": spec["publish_date"],
        "updated_at": spec["effective_date"],
        "doc_type": "PDF正式制度",
        "source_type": "pdf",
        "policy_no": spec["policy_no"],
        "company": COMPANY_NAME,
        "cross_refs": ",".join(spec["cross_refs"]),
    }


def eval_cases_for(spec: dict) -> Iterable[dict]:
    slug = spec["doc_id"].lower().replace("pdf-", "").replace("-", "_")
    base = {"expected_doc_ids": [spec["doc_id"]], "department": spec["department"], "should_refuse": False}
    sections = [item["title"] for item in spec["sections"]]
    cases = [
        {
            "id": f"{slug}_scope",
            "question": f"{spec['title']}适用于哪些人员或场景？",
            "expected_sections": [sections[0]],
            "reference_answer": f"适用范围包括{spec['scope']}。",
            "question_type": "PDF-事实型",
        },
        {
            "id": f"{slug}_sla",
            "question": f"{spec['title']}的审批或办理时限是什么？",
            "expected_sections": ["审批流程"],
            "reference_answer": f"标准办理时限为：{spec['approval_sla']}。",
            "question_type": "PDF-时限型",
        },
        {
            "id": f"{slug}_materials",
            "question": f"办理{spec['process_type']}需要提交哪些材料？",
            "expected_sections": ["附件一"],
            "reference_answer": spec["material_answer"],
            "question_type": "PDF-材料型",
        },
        {
            "id": f"{slug}_exception",
            "question": f"{spec['process_type']}遇到紧急或例外情况怎么处理？",
            "expected_sections": [spec["exception_section"]],
            "reference_answer": spec["exception_answer"],
            "question_type": "PDF-例外条件型",
        },
        {
            "id": f"{slug}_cross_ref",
            "question": f"{spec['title']}和哪些制度存在交叉引用？",
            "expected_sections": [spec["cross_ref_section"]],
            "reference_answer": f"相关制度包括：{','.join(spec['cross_refs'])}。",
            "question_type": "PDF-跨文档引用型",
        },
        {
            "id": f"{slug}_version",
            "question": f"{spec['title']}当前版本和生效日期是什么？",
            "expected_sections": ["修订记录"],
            "reference_answer": f"当前版本为{spec['version']}，自{spec['effective_date']}起生效。",
            "question_type": "PDF-版本差异型",
        },
    ]
    for case in cases:
        case.update(base)
        yield case


def generate_pdf(spec: dict, styles: dict) -> None:
    doc = SimpleDocTemplate(
        str(PDF_DIR / spec["filename"]),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
    )
    doc.build(
        build_formal_story(spec, styles),
        onFirstPage=lambda canvas, document: header_footer(canvas, document, spec),
        onLaterPages=lambda canvas, document: header_footer(canvas, document, spec),
    )
    (PDF_DIR / spec["filename"]).with_suffix(".metadata.json").write_text(
        json.dumps(metadata_for(spec), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_base_spec(**kwargs) -> dict:
    spec = {
        "risk_level": "中",
        "approval_flow": [],
        "revision_history": [],
        "appendices": [],
        "page_break_after": [],
    }
    spec.update(kwargs)
    return spec


PDF_SPECS = [
    make_base_spec(
        filename="employee_handbook_2026.pdf",
        doc_id="PDF-HR-HANDBOOK-2026",
        title="员工手册",
        department="HR",
        process_type="员工行为与劳动纪律管理",
        owner="人力资源部",
        system="员工服务系统",
        form_id="HR-F-000",
        approval_sla="员工手册争议解释应在五个工作日内反馈",
        scope="全体正式员工、试用期员工、实习生及签署公司管理协议的外部协作人员",
        policy_no="HR-HANDBOOK-2026-01",
        version="V3.0",
        publish_date="2026年1月5日",
        effective_date="2026-02-01",
        cross_refs=["PDF-HR-ATT-2026", "PDF-HR-LEAVE-PDF-2026", "PDF-HR-PERF-2026", "PDF-SEC-INFO-2026"],
        revision_history=[
            ["V2.4", "2025年4月1日", "补充远程协作纪律、信息安全红线和奖惩衔接条款。", "人力资源负责人"],
            ["V3.0", "2026年1月5日", "重构员工行为准则、利益冲突申报、申诉复核和制度适用顺序。", "管理委员会"],
        ],
        approval_flow=[
            {"step": "制度解释申请", "role": "员工或主管", "requirement": "在员工服务系统提交争议背景、涉及条款、事实材料和期望解释。", "sla": "T日"},
            {"step": "HR 初审", "role": "HRBP", "requirement": "判断是否属于员工手册范围，必要时转入专项制度负责人。", "sla": "2个工作日"},
            {"step": "联合复核", "role": "人力资源部/法务/内审", "requirement": "涉及纪律处分、劳动争议或信息安全事件时进行联合复核。", "sla": "5个工作日"},
            {"step": "归档反馈", "role": "人力资源部", "requirement": "输出书面解释并归档至员工档案。", "sla": "1个工作日"},
        ],
        sections=[
            {"title": "总则与适用原则", "clauses": [
                "为建立清晰、公平、可追溯的员工行为管理机制，维护公司运营秩序和员工合法权益，制定本手册。",
                "本手册适用于公司全体员工及受公司管理要求约束的外部协作人员；外包驻场人员另有合同约定的，从其约定。",
                "员工应遵守诚实信用、勤勉尽责、信息保密、利益回避和尊重协作的基本原则。",
                "本手册与专项制度不一致时，优先适用事项更具体、发布时间更新且审批层级更高的制度。",
            ]},
            {"title": "员工行为准则", "clauses": [
                "员工应按岗位职责履行工作义务，不得无故拒绝合理工作安排或故意拖延跨部门协作事项。",
                "员工不得利用职务便利为本人、亲属、关联方或外部供应商谋取不当利益。",
                "员工在客户沟通、供应商接触、媒体发言和公开平台表达时，应维护公司声誉，不得擅自承诺制度外权益。",
                "员工不得伪造考勤、报销、绩效、培训或审批记录；发现系统异常应及时反馈，不得利用漏洞获利。",
                "员工应妥善保管办公设备、账号凭证、客户资料和内部文件，离岗、转岗或离职时按要求完成交接。",
            ]},
            {"title": "利益冲突与廉洁要求", "clauses": [
                "员工本人或近亲属与供应商、客户、竞品公司存在投资、任职、顾问或亲属关系的，应主动申报。",
                "员工不得收受可能影响独立判断的礼金、购物卡、旅游安排、宴请或其他不当利益。",
                "确因商务礼仪无法拒收的礼品，应在三个工作日内向直属主管和内审部登记，由公司统一处理。",
                "涉及采购、招投标、合同评审、资金支付和人员录用的岗位，应执行更高标准的利益回避要求。",
            ]},
            {"title": "劳动纪律与奖惩处理", "clauses": [
                "轻微违规以提醒、培训、书面警示等方式处理；严重违规可根据情节采取降级、调岗、解除劳动合同等措施。",
                "员工连续或重复违反考勤、信息安全、报销或客户服务制度的，可合并评估违规情节。",
                "处理纪律事项前，相关部门应收集事实材料、系统记录、沟通记录和当事人说明，确保处理依据完整。",
                "涉及客户数据泄露、商业贿赂、财务舞弊、故意破坏系统或泄露商业秘密的，应立即升级至高风险事件处理。",
                "员工对处理结果有异议的，可在收到结果后五个工作日内提交书面申诉。",
            ]},
            {"title": "专项制度衔接", "clauses": [
                "考勤、休假、绩效、报销、信息安全、采购、合同和数据处理等事项，优先适用对应专项制度。",
                "同一行为同时违反多项制度的，归口部门应联合确认主责制度、责任类型和处理顺序。",
                "涉及员工隐私、劳动关系或纪律处分的材料，应限定知悉范围，不得在非必要群组传播。",
                "本手册作为通用制度，不替代法律法规、劳动合同、保密协议和岗位责任书。",
            ]},
            {"title": "申诉、复核与归档", "clauses": [
                "员工申诉应说明事实、理由、证据和诉求，不得仅以情绪表达替代事实说明。",
                "申诉复核期间，原处理决定原则上继续执行；确有重大事实争议的，可由人力资源部决定暂缓执行。",
                "复核结论应形成书面记录，并归档至员工档案或专项事件档案。",
                "本手册由人力资源部负责解释，并根据业务变化、员工反馈和审计结果定期修订。",
            ]},
        ],
        page_break_after=[2, 4],
        appendices=[
            {"title": "利益冲突申报表", "widths": [35, 42, 42, 51], "rows": [
                ["字段", "填写要求", "提交人", "说明"],
                ["关联关系", "供应商、客户、竞品或候选人关系", "员工", "须说明本人或近亲属关系"],
                ["涉及事项", "采购、合同、招聘、评审、付款等", "员工", "列明流程编号和事项背景"],
                ["回避建议", "是否退出评审或审批", "直属主管", "由主管提出初步意见"],
            ]},
            {"title": "纪律处分材料清单", "widths": [42, 28, 24, 76], "rows": [
                ["材料名称", "责任人", "是否必填", "说明"],
                ["事实说明", "主管", "是", "记录时间、地点、行为、影响范围"],
                ["系统证据", "执行部门", "视情况", "包括考勤、审批、日志、邮件等记录"],
                ["员工陈述", "员工本人", "是", "员工可说明事实和异议"],
            ]},
        ],
        material_answer="员工手册争议处理通常需要提交争议背景、涉及条款、事实材料、系统记录和员工陈述。",
        exception_section="劳动纪律与奖惩处理",
        exception_answer="涉及严重违规或高风险事件时，应立即升级至人力资源、法务、内审或信息安全联合处理，并保留事实材料。",
        cross_ref_section="专项制度衔接",
    ),
    make_base_spec(
        filename="attendance_policy_2026.pdf",
        doc_id="PDF-HR-ATT-2026",
        title="员工考勤管理制度",
        department="HR",
        process_type="考勤管理",
        owner="人力资源部",
        system="员工服务系统",
        form_id="HR-F-101",
        approval_sla="考勤异常申诉应在三个工作日内提交",
        scope="全体正式员工、试用期员工、实习生，以及按公司排班接受管理的外部协作人员",
        policy_no="HR-ATT-2026-01",
        version="V2.1",
        publish_date="2026年1月10日",
        effective_date="2026-02-01",
        cross_refs=["PDF-HR-LEAVE-PDF-2026", "PDF-HR-HANDBOOK-2026", "PDF-HR-REMOTE-2026"],
        revision_history=[
            ["V1.7", "2025年7月1日", "调整外勤打卡、补卡次数和迟到处理规则。", "人力资源负责人"],
            ["V2.1", "2026年1月10日", "增加弹性到岗窗口、远程办公考勤衔接和异常申诉时限。", "人力资源负责人"],
        ],
        approval_flow=[
            {"step": "异常提交", "role": "员工", "requirement": "在员工服务系统选择迟到、漏打卡、外勤、远程办公等类型并上传证明。", "sla": "3个工作日内"},
            {"step": "主管确认", "role": "直属主管", "requirement": "确认员工实际工作状态、到岗时间和业务原因。", "sla": "1个工作日"},
            {"step": "HR 复核", "role": "HRBP", "requirement": "核对排班、请假、远程办公和历史异常记录。", "sla": "2个工作日"},
            {"step": "结果归档", "role": "人力资源部", "requirement": "将结果同步至月度考勤台账和薪酬计算。", "sla": "月度结算前"},
        ],
        sections=[
            {"title": "考勤周期与工时规则", "clauses": [
                "标准考勤周期按自然月计算，日常工作时间、午休安排和特殊排班以员工服务系统发布为准。",
                "研发、产品、数据分析岗位自二零二六年二月一日起可适用三十分钟弹性到岗窗口，但每日标准工作时长不得减少。",
                "客服、运维、财务结算和现场支持岗位因排班连续性要求，是否适用弹性到岗由部门负责人和人力资源部共同确认。",
                "因项目上线、月结、客户现场或应急响应产生加班的，应事前申请；紧急情况可事后一个工作日内补提。",
            ]},
            {"title": "打卡、外勤与远程办公记录", "clauses": [
                "员工应使用公司指定系统完成上下班打卡，不得代打卡、伪造定位或借用他人设备。",
                "外勤人员应在到达客户现场、离开客户现场或返回办公地点时分别记录位置，并补充客户或项目名称。",
                "远程办公期间应按批准时段保持在线协作，并通过公司 VPN 或受控终端处理内部资料。",
                "因系统故障无法打卡的，员工应在当天提交异常说明并附系统截图或主管证明。",
                "同一员工月度补卡超过三次的，HRBP 应提示直属主管关注排班安排和工作纪律。",
            ]},
            {"title": "迟到、早退与旷工认定", "clauses": [
                "月度迟到三次以内且单次不超过十分钟的，记录为提醒；超过三次或单次超过三十分钟的，应提交异常说明。",
                "未经批准提前离岗超过三十分钟的，按早退处理；影响客户服务、系统值守或交付节点的，应同步评估业务影响。",
                "连续旷工或年度累计旷工达到员工手册规定阈值的，按严重违纪流程处理。",
                "因交通管制、极端天气、突发公共事件导致集中迟到的，人力资源部可发布统一豁免口径。",
            ]},
            {"title": "请假、出差与考勤衔接", "clauses": [
                "已通过休假流程审批的时段，不再重复提交考勤异常申诉；系统未同步的，员工可提交关联单号。",
                "出差期间的考勤以差旅审批单、行程记录和业务负责人确认为准。",
                "员工因病假、婚假、产检假等原因不能正常打卡的，应按休假管理办法提交证明材料。",
                "跨城市临时办公超过三个工作日的，应同步提交远程办公或异地协作申请。",
            ]},
            {"title": "异常申诉与月度结算", "clauses": [
                "考勤异常申诉应在异常发生后三个工作日内提交，逾期原则上不再调整，但系统故障或不可抗力除外。",
                "主管审批考勤异常时，应确认员工是否实际履行工作职责，不得仅因人情原因通过。",
                "HRBP 每月结算前应抽查补卡、外勤、远程办公和加班记录，对异常集中部门进行提醒。",
                "考勤结果影响薪酬、绩效或纪律处理的，应保留系统记录和审批意见。",
            ]},
        ],
        page_break_after=[2, 4],
        appendices=[
            {"title": "考勤异常申诉材料清单", "widths": [42, 30, 28, 70], "rows": [
                ["异常类型", "证明材料", "提交时限", "说明"],
                ["漏打卡", "系统截图或主管证明", "3个工作日", "每月超过三次触发 HR 复核"],
                ["外勤", "客户现场记录或项目说明", "当天", "应包含地点和联系人"],
                ["远程办公", "远程办公审批单", "事前或当天", "连续超过三天须提前申请"],
            ]},
            {"title": "考勤处理口径表", "widths": [38, 42, 42, 48], "rows": [
                ["情形", "认定口径", "处理方式", "例外条件"],
                ["迟到十分钟内", "月度三次以内提醒", "记录提醒", "极端天气统一豁免"],
                ["迟到三十分钟以上", "需主管确认", "异常申诉或扣减", "客户现场延误需证明"],
                ["代打卡", "严重违规", "纪律处理", "无例外"],
            ]},
        ],
        material_answer="考勤异常通常需要提交异常类型说明、系统截图、外勤或客户现场证明、远程办公审批单以及主管确认意见。",
        exception_section="异常申诉与月度结算",
        exception_answer="系统故障、不可抗力或公司统一发布豁免口径时，可以在说明原因和提供证明后按例外处理。",
        cross_ref_section="请假、出差与考勤衔接",
    ),
]


def extend_specs_with_domain_documents() -> None:
    extra_specs = [
        {
            "filename": "leave_policy_2026.pdf",
            "doc_id": "PDF-HR-LEAVE-PDF-2026",
            "title": "员工休假管理办法",
            "department": "HR",
            "process_type": "休假申请",
            "risk_level": "中",
            "owner": "人力资源部",
            "system": "员工服务系统",
            "form_id": "HR-F-102",
            "approval_sla": "年假连续超过五个工作日须提前七个工作日提交",
            "scope": "正式员工、试用期员工、实习生及按劳动合同约定享有休假权益的人员",
            "policy_no": "HR-LEAVE-2026-02",
            "version": "V2.0",
            "publish_date": "2026年1月12日",
            "effective_date": "2026-02-01",
            "cross_refs": ["PDF-HR-ATT-2026", "PDF-HR-HANDBOOK-2026"],
            "revision_history": [["V1.5", "2025年5月1日", "补充病假证明、婚假材料和调休有效期。", "人力资源负责人"], ["V2.0", "2026年1月12日", "区分正式员工、试用期员工和实习生休假口径。", "人力资源负责人"]],
            "approval_flow": [
                {"step": "休假申请", "role": "员工", "requirement": "选择假别、填写起止时间、交接安排并上传证明。", "sla": "事前提交"},
                {"step": "业务确认", "role": "直属主管", "requirement": "确认工作交接、排班影响和客户承诺。", "sla": "1个工作日"},
                {"step": "HR 复核", "role": "HRBP", "requirement": "核对假别余额、证明材料和政策适用条件。", "sla": "2个工作日"},
                {"step": "假期归档", "role": "人力资源部", "requirement": "同步考勤和薪酬系统。", "sla": "月度结算前"},
            ],
            "sections": [
                {"title": "假别分类与适用条件", "clauses": ["年假、病假、婚假、产假、陪产假、丧假、调休和事假分别适用不同申请条件。", "正式员工连续服务满一年后享有年假；试用期员工原则上不安排年假，确需休假的按事假处理。", "实习生请假按实习协议和部门排班要求执行，不纳入年假余额计算。", "法定假期按照国家规定执行，公司可根据业务连续性安排值班或调休。"]},
                {"title": "年假与调休管理", "clauses": ["年假应优先在当年度内使用，确因业务原因未能休完的，可按公司年度通知结转。", "年假连续超过五个工作日的，应至少提前七个工作日提交申请。", "调休应来源于已审批加班记录，原则上自加班发生之日起六个月内使用。", "关键岗位在系统上线、财务月结、重大客户交付期间休假，应提前完成交接并经部门负责人确认。"]},
                {"title": "病假、婚假与特殊假", "clauses": ["病假应上传医疗机构证明，连续病假超过三日的，应补充诊断证明或复诊记录。", "婚假申请应上传结婚登记证明，并在登记后一年内一次性或分段使用。", "产检假、产假、陪产假和哺乳假按所在地法规及公司补充规定执行。", "丧假应说明亲属关系和请假时间，必要时可补充证明材料。"]},
                {"title": "工作交接与审批限制", "clauses": ["休假申请应说明待办事项、代理人和紧急联系人，不得仅提交空白申请。", "主管审批时应评估排班、客户承诺、系统值守和项目交付影响。", "员工休假期间原则上不安排日常会议，确因紧急事项联系的，应尊重员工休假权益。", "未完成交接且可能影响重大事项的，主管可要求调整休假安排并说明理由。"]},
                {"title": "例外处理与撤销变更", "clauses": ["突发疾病、家庭紧急事件或不可抗力导致无法事前申请的，可事后一日内补提。", "休假计划发生变化的，应在系统内撤销或变更原申请，不得仅通过聊天消息通知。", "员工已休假但材料不齐的，HRBP 可要求补充材料，拒不补充的可按事假或旷工处理。", "跨制度争议按考勤管理制度、员工手册和本办法共同确认。"]},
            ],
            "page_break_after": [2, 4],
            "appendices": [
                {"title": "假别材料要求表", "widths": [30, 45, 35, 60], "rows": [["假别", "证明材料", "提交时点", "说明"], ["年假", "交接安排", "事前", "连续超过五个工作日提前七个工作日"], ["病假", "医疗证明", "返岗后三个工作日内", "连续超过三日补充诊断证明"], ["婚假", "结婚登记证明", "事前", "登记后一年内使用"]]},
                {"title": "休假交接清单", "widths": [42, 42, 36, 50], "rows": [["事项", "代理人", "风险等级", "交接说明"], ["客户承诺", "项目负责人", "高", "列明交付时间和联系人"], ["系统值守", "值班人员", "中", "说明告警和升级路径"], ["审批待办", "直属主管", "中", "列明待处理流程编号"]]},
            ],
            "material_answer": "休假申请通常需要提交假别、起止时间、交接安排、证明材料和主管确认意见。",
            "exception_section": "例外处理与撤销变更",
            "exception_answer": "突发疾病、家庭紧急事件或不可抗力可事后补提，但应说明原因并在规定时间内补齐材料。",
            "cross_ref_section": "例外处理与撤销变更",
        },
        {
            "filename": "expense_reimbursement_2026.pdf",
            "doc_id": "PDF-FIN-EXP-2026",
            "title": "费用报销与票据管理制度",
            "department": "Finance",
            "process_type": "报销申请",
            "risk_level": "中",
            "owner": "财务部",
            "system": "财务共享平台",
            "form_id": "FIN-F-201",
            "approval_sla": "普通报销应在费用发生后三十日内提交",
            "scope": "因公产生差旅、招待、办公采购、培训会议、客户活动等费用的员工",
            "policy_no": "FIN-EXP-2026-01",
            "version": "V3.2",
            "publish_date": "2026年1月15日",
            "effective_date": "2026-02-01",
            "cross_refs": ["FIN-BUDGET-2026", "ADM-TRAVEL-2026", "PDF-PROC-PURCHASE-2026"],
            "revision_history": [["V2.8", "2025年8月1日", "调整电子发票验真和差旅报销附件要求。", "财务负责人"], ["V3.2", "2026年1月15日", "补充预算占用、超标费用、招待费和预付款核销规则。", "财务负责人"]],
            "approval_flow": [
                {"step": "费用提交", "role": "报销人", "requirement": "填写费用类型、成本中心、预算项目、票据和业务说明。", "sla": "30日内"},
                {"step": "主管审批", "role": "直属主管", "requirement": "确认费用真实性、业务必要性和标准合规性。", "sla": "2个工作日"},
                {"step": "财务审核", "role": "费用会计", "requirement": "核验发票、预算、附件和重复报销风险。", "sla": "3个工作日"},
                {"step": "付款归档", "role": "出纳/档案岗", "requirement": "付款后归档票据影像和审批流水。", "sla": "付款后1个工作日"},
            ],
            "sections": [
                {"title": "费用范围与预算控制", "clauses": ["报销费用应真实、合理、与公司业务相关，并已纳入预算或取得预算追加批准。", "单笔招待费用超过五千元或单次差旅费用超过两万元的，应在报销前完成预算确认。", "无预算、超预算或预算科目不匹配的费用，财务有权退回补充说明。", "个人消费、家庭支出、罚款滞纳金和制度外福利不得报销。"]},
                {"title": "票据合规与影像归档", "clauses": ["电子发票应保证抬头、税号、金额、日期和消费事项一致，不得重复提交同一票据。", "纸质发票应保持票面完整，粘贴或扫描应清晰可识别。", "境外票据应补充付款凭证、汇率说明和业务证明。", "财务共享平台中的影像记录为报销归档依据，不得事后替换核心票据。", "发票异常、抬头错误或金额不一致的，应退回补正或按无票据流程处理。"]},
                {"title": "差旅、招待和会议费用", "clauses": ["差旅费用应关联出差申请单，住宿、交通、餐补按差旅制度标准执行。", "客户招待应说明客户名称、参与人员、业务目的和预计收益。", "会议培训费用应提供会议通知、签到或培训证明。", "多人共同发生费用的，应由一人统一报销并列明分摊人员。"]},
                {"title": "超标、逾期与例外报销", "clauses": ["普通报销应在费用发生后三十日内提交，逾期应说明原因并经部门负责人确认。", "超标准费用应事前审批；因紧急客户事项无法事前审批的，应在三个工作日内补充说明。", "丢失发票的，应提交无法取得票据说明、付款凭证和业务证明，并经财务负责人审批。", "同一事项拆分报销规避审批阈值的，按违规处理。"]},
                {"title": "付款、核销与审计", "clauses": ["报销审批通过后，由财务按付款批次执行支付。", "涉及预付款、备用金或借款的，应在事项结束后及时核销。", "财务和内审可对高频报销、异常供应商、重复票据和超标费用进行抽查。", "发现虚假报销、重复报销或挪用资金的，应移交员工纪律处理流程。"]},
            ],
            "page_break_after": [2, 4],
            "appendices": [
                {"title": "报销材料清单", "widths": [38, 40, 28, 64], "rows": [["费用类型", "必备材料", "系统字段", "说明"], ["差旅费", "出差单、行程、发票", "成本中心", "住宿和交通按标准"], ["招待费", "客户名单、业务说明、发票", "预算项目", "超五千元需事前确认"], ["会议培训", "通知、签到、发票", "费用科目", "内部培训可附审批单"]]},
                {"title": "票据审核要点", "widths": [42, 42, 36, 50], "rows": [["检查项", "风险表现", "处理方式", "责任人"], ["重复票据", "同一发票多次提交", "退回并标记", "费用会计"], ["抬头错误", "非公司抬头", "要求重开", "报销人"], ["金额异常", "票面与申请不一致", "补充说明", "财务审核"]]},
            ],
            "material_answer": "报销通常需要提交发票、业务说明、预算项目、审批单、付款凭证或行程会议证明。",
            "exception_section": "超标、逾期与例外报销",
            "exception_answer": "超标或逾期报销须说明原因并取得部门负责人或财务负责人确认，紧急事项应在三个工作日内补充材料。",
            "cross_ref_section": "费用范围与预算控制",
        },
    ]

    PDF_SPECS.extend(make_base_spec(**item) for item in extra_specs)


def clone_domain_spec(base: dict, overrides: dict) -> dict:
    spec = deepcopy(base)
    spec.update(overrides)
    return make_base_spec(**spec)


def add_remaining_specs() -> None:
    security_base = {
        "department": "Security",
        "risk_level": "高",
        "owner": "信息安全部",
        "approval_flow": [
            {"step": "申请提交", "role": "申请人", "requirement": "说明业务目的、数据或权限范围、使用期限和风险控制措施。", "sla": "T日"},
            {"step": "主管确认", "role": "直属主管", "requirement": "确认业务必要性和最小权限范围。", "sla": "1个工作日"},
            {"step": "安全复核", "role": "信息安全部", "requirement": "评估数据敏感级别、权限影响、日志审计和例外条件。", "sla": "2至5个工作日"},
            {"step": "执行归档", "role": "系统管理员", "requirement": "执行开通、导出或关闭，并回填日志编号。", "sla": "执行后1个工作日"},
        ],
        "page_break_after": [2, 4],
    }
    remaining = [
        clone_domain_spec(security_base, {
            "filename": "information_security_2026.pdf", "doc_id": "PDF-SEC-INFO-2026", "title": "信息安全与账号权限管理制度", "process_type": "账号权限", "system": "权限管理平台", "form_id": "SEC-F-301", "approval_sla": "高权限账号申请须至少提前两个工作日提交", "scope": "所有使用公司系统、网络、数据和账号权限的人员", "policy_no": "SEC-INFO-2026-01", "version": "V2.4", "publish_date": "2026年1月18日", "effective_date": "2026-02-01", "cross_refs": ["PDF-SEC-DATAEXPORT-2026", "IT-PERM-2026", "PDF-HR-ONOFF-2026"], "revision_history": [["V2.0", "2025年6月1日", "新增共享账号禁用和权限复核要求。", "信息安全负责人"], ["V2.4", "2026年1月18日", "补充高权限账号、外包人员账号和离职权限关闭规则。", "信息安全负责人"]], "sections": [
                {"title": "账号分类与最小权限", "clauses": ["账号分为普通办公账号、业务系统账号、生产运维账号、管理员账号和临时协作账号。", "权限申请应遵循最小权限原则，申请范围不得超过岗位职责和业务事项需要。", "共享账号原则上禁止使用，因系统限制确需使用的，应指定责任人并开启操作日志审计。", "外包人员账号应设置到期日，到期未续期的系统自动停用。"]},
                {"title": "高权限申请与复核", "clauses": ["生产系统、客户数据、财务数据和管理员权限属于高风险权限。", "高权限账号申请须至少提前两个工作日提交，并说明操作场景、有效期和回收时间。", "安全复核应检查是否存在替代低权限方案、是否需要双人复核和是否开启日志审计。", "长期高权限每季度至少复核一次，发现岗位变化或长期未使用的，应立即回收。"]},
                {"title": "密码、终端与网络要求", "clauses": ["员工不得与他人共享密码、验证码、令牌或 MFA 设备。", "处理内部资料的终端应安装公司安全组件，不得擅自关闭防护策略。", "公共网络环境访问内部系统应使用公司 VPN，禁止通过个人代理或未授权远程桌面接入。", "发现账号异常登录、设备丢失或疑似钓鱼攻击时，应立即上报信息安全部。"]},
                {"title": "入离职与权限回收", "clauses": ["新员工账号应根据岗位模板开通，超出模板的权限需单独审批。", "转岗员工应重新确认权限，原岗位权限应在转岗生效后三个工作日内回收。", "离职员工权限应在离职当天关闭，涉密岗位可根据交接计划提前冻结敏感权限。", "未按时回收权限导致风险事件的，系统负责人和直属主管承担管理责任。"]},
                {"title": "审计、违规与例外", "clauses": ["信息安全部可对高权限操作、异常登录、批量下载和越权访问进行审计。", "紧急生产故障可使用临时权限，但应限定时长并在事后二十四小时内补齐审批。", "未经授权访问、复制或传播客户数据的，按高风险安全事件处理。", "本制度与数据导出制度、入离职流程和员工手册共同适用。"]},
            ], "appendices": [{"title": "权限申请材料表", "widths": [40, 42, 32, 56], "rows": [["材料", "内容", "提交人", "说明"], ["权限范围", "系统、角色、数据范围", "申请人", "必须最小化"], ["有效期", "起止时间", "申请人", "临时权限必填"], ["风险措施", "日志、双人复核、回收计划", "系统负责人", "高权限必填"]]}], "material_answer": "账号权限申请需要提交权限范围、业务目的、有效期、风险控制措施和主管确认意见。", "exception_section": "审计、违规与例外", "exception_answer": "紧急生产故障可使用临时权限，但应限定时长并在二十四小时内补齐审批。", "cross_ref_section": "审计、违规与例外"}),
        clone_domain_spec(security_base, {
            "filename": "data_export_policy_2026.pdf", "doc_id": "PDF-SEC-DATAEXPORT-2026", "title": "客户数据导出与外发审批制度", "process_type": "数据导出", "owner": "信息安全部与法务部", "system": "数据安全审批平台", "form_id": "SEC-F-302", "approval_sla": "含客户身份信息的数据导出须至少提前三个工作日提交", "scope": "客户数据、业务明细、日志数据、分析报表和需要外发的数据文件", "policy_no": "SEC-DATA-2026-01", "version": "V2.7", "publish_date": "2026年2月5日", "effective_date": "2026-02-15", "cross_refs": ["PDF-SEC-INFO-2026", "PDF-AI-USAGE-2026", "PDF-LEGAL-RETENTION-2026"], "revision_history": [["V2.1", "2025年9月1日", "增加外发水印和接收方确认要求。", "信息安全负责人"], ["V2.7", "2026年2月5日", "补充客户身份信息导出、脱敏评估和跨境限制。", "信息安全负责人"]], "sections": [
                {"title": "数据分类与导出边界", "clauses": ["数据按公开、内部、敏感和受限四级管理，客户身份信息、交易记录和行为日志属于敏感或受限数据。", "导出应有明确业务目的、使用期限和接收对象，不得以备份、个人分析或沟通方便为由扩大范围。", "分析报表若无法识别个人身份且不含商业敏感字段，可按内部数据流程审批。", "导出前应确认是否存在可替代的系统查询、权限开放或脱敏数据集。"]},
                {"title": "脱敏、加密与外发控制", "clauses": ["导出客户身份信息、联系方式、交易记录或行为日志前，应完成脱敏评估和接收方确认。", "外发文件应使用公司批准的加密方式、水印策略和有效期控制。", "未经审批不得通过个人邮箱、网盘、即时通讯工具或移动存储设备外发客户数据。", "外部接收方应签署保密或数据处理协议，法务可根据场景要求补充条款。"]},
                {"title": "审批等级与复核要求", "clauses": ["含客户身份信息的数据导出须至少提前三个工作日提交。", "批量超过一万条记录、涉及跨境传输或监管敏感行业客户的，应升级至信息安全部和法务部联合审批。", "临时导出权限应设置有效期，到期后系统自动关闭。", "审批人应核对字段清单、样例数据、使用目的和销毁计划。"]},
                {"title": "交付、留存与销毁", "clauses": ["数据交付后，申请人应确认接收方、交付时间、文件哈希或水印编号。", "外发数据应按批准期限使用，到期后由接收方反馈销毁或归档确认。", "涉及争议、审计或监管调查的数据不得提前销毁。", "数据导出审批流水、字段清单和交付记录应至少保存五年。"]},
                {"title": "紧急导出与违规处理", "clauses": ["客户重大故障、监管报送或安全事件可启动紧急导出，但必须记录原因、范围和后补审批计划。", "紧急导出应优先采用最小字段、最短期限和受控传输方式。", "擅自外发客户数据、绕过脱敏或扩大使用范围的，按高风险安全事件处理。", "本制度与信息安全制度、AI 使用规范和业务记录留存制度共同适用。"]},
            ], "appendices": [{"title": "数据导出字段评估表", "widths": [36, 36, 32, 66], "rows": [["字段类型", "敏感级别", "处理方式", "说明"], ["客户姓名/证件", "受限", "原则上脱敏", "确需明文需法务复核"], ["联系方式", "敏感", "掩码或哈希", "外发需接收方确认"], ["统计指标", "内部", "汇总输出", "不得反推个人"]]}], "material_answer": "数据导出需要提交字段清单、业务目的、接收方信息、脱敏方案、使用期限和销毁计划。", "exception_section": "紧急导出与违规处理", "exception_answer": "重大故障、监管报送或安全事件可紧急导出，但必须记录原因、范围和后补审批计划。", "cross_ref_section": "紧急导出与违规处理"}),
    ]
    PDF_SPECS.extend(remaining)


def add_compact_specs() -> None:
    compact_specs = [
        ("performance_review_2026.pdf", "PDF-HR-PERF-2026", "绩效考核与申诉管理办法", "HR", "绩效考核", "人力资源部", "绩效管理系统", "HR-F-103", "绩效申诉应在结果发布后五个工作日内提交", "纳入季度或年度绩效考核的正式员工和试用期员工", "HR-PERF-2026-01", "V2.2", "2026年1月20日", "2026-02-01", ["PDF-HR-HANDBOOK-2026"], ["目标设定与过程反馈", "评分校准与等级分布", "绩效面谈与改进计划", "申诉受理与复核机制", "结果应用与归档"]),
        ("onboarding_offboarding_2026.pdf", "PDF-HR-ONOFF-2026", "员工入离职流程说明", "HR", "入离职流程", "人力资源部与信息技术部", "员工服务系统", "HR-F-104", "入职账号应在入职日前两个工作日完成预开通", "正式员工、试用期员工、实习生和外包驻场人员", "HR-ONOFF-2026-01", "V1.8", "2026年1月22日", "2026-02-01", ["PDF-SEC-INFO-2026", "IT-ASSET-2026"], ["入职准备与材料核验", "账号、设备与权限开通", "试用期跟进与岗位交接", "离职申请与工作交接", "权限关闭、资产归还与档案归档"]),
        ("remote_work_policy_2026.pdf", "PDF-HR-REMOTE-2026", "远程办公与异地协作管理规范", "HR", "远程办公", "人力资源部与信息安全部", "员工服务系统", "HR-F-105", "连续远程办公超过三天须至少提前两个工作日提交申请", "居家办公、异地办公、跨城市协作、临时远程接入和外部网络使用", "HR-REMOTE-2026-01", "V2.0", "2026年1月25日", "2026-02-01", ["PDF-SEC-INFO-2026", "PDF-HR-ATT-2026"], ["远程办公适用场景", "申请审批与工作记录", "设备、网络与数据安全", "跨境远程办公限制", "协作质量与例外撤销"]),
        ("open_source_compliance_2026.pdf", "PDF-IT-OSS-2026", "开源软件引入与许可证合规规范", "IT", "开源合规", "技术委员会与法务部", "研发资产管理平台", "IT-F-401", "引入 GPL/AGPL 类许可证组件须在上线前五个工作日完成法务复核", "开源组件选型、许可证审查、漏洞扫描、版本升级、二次分发和开源义务履行", "IT-OSS-2026-01", "V2.3", "2026年1月26日", "2026-02-01", ["PDF-SEC-INFO-2026"], ["开源组件准入", "许可证识别与法律复核", "漏洞扫描与版本维护", "二次分发和开源义务", "例外审批与资产台账"]),
        ("ai_usage_governance_2026.pdf", "PDF-AI-USAGE-2026", "生成式AI工具使用与内容审核规范", "AI Governance", "AI工具使用", "AI治理委员会", "AI工具申请平台", "AI-F-501", "高风险AI使用场景须在上线前五个工作日完成审核", "员工使用生成式AI工具进行文案、代码、数据分析、客户沟通辅助和知识检索的场景", "AI-USAGE-2026-01", "V1.5", "2026年1月28日", "2026-02-01", ["PDF-SEC-DATAEXPORT-2026", "PDF-SEC-INFO-2026"], ["AI工具分级与准入", "禁止输入的信息类型", "内容审核与人工复核", "代码、数据与客户场景限制", "日志留存与违规处理"]),
        ("records_retention_2026.pdf", "PDF-LEGAL-RETENTION-2026", "业务记录留存与销毁管理规范", "Legal", "记录留存", "法务部与内审部", "档案管理系统", "LEG-F-601", "高风险业务记录销毁须提前十个工作日发起审批", "合同、审批记录、客服录音、财务凭证、系统日志、监管报送材料和项目归档资料", "LEG-RET-2026-01", "V2.6", "2026年1月30日", "2026-02-01", ["LEGAL-CONTRACT-2026", "PDF-OPS-CS-QUALITY-2026"], ["记录分类与保存期限", "电子档案和纸质档案管理", "冻结留存与诉讼保全", "销毁审批和见证", "抽查、审计与责任追究"]),
        ("customer_service_quality_2026.pdf", "PDF-OPS-CS-QUALITY-2026", "客户服务话术质检与升级处理规范", "Operations", "客服质检", "客户运营部", "客服质检平台", "OPS-F-701", "重大客诉须在两个小时内完成升级登记", "客服会话质检、话术合规、客户投诉升级、敏感问题复核和服务质量改进", "OPS-CS-2026-01", "V2.0", "2026年2月1日", "2026-02-15", ["PDF-SEC-INFO-2026", "PDF-LEGAL-RETENTION-2026"], ["质检范围与抽样比例", "话术红线和承诺边界", "重大客诉升级", "录音和会话记录留存", "整改闭环与质量评分"]),
        ("procurement_policy_2026.pdf", "PDF-PROC-PURCHASE-2026", "采购申请与供应商准入管理制度", "Procurement", "采购申请", "采购部与财务部", "采购管理平台", "PROC-F-801", "单笔金额超过十万元的采购应提前五个工作日发起评审", "办公采购、软件服务、咨询服务、外包服务、硬件设备和供应商准入", "PROC-PUR-2026-01", "V2.1", "2026年2月3日", "2026-02-15", ["FIN-BUDGET-2026", "PDF-FIN-EXP-2026"], ["采购分类与预算前置", "询比价和招投标", "供应商准入与廉洁承诺", "合同、验收与付款衔接", "紧急采购和拆单风险"]),
        ("business_continuity_2026.pdf", "PDF-OPS-BCP-2026", "业务连续性演练与应急响应制度", "Operations", "业务连续性", "运营管理部与信息技术部", "应急响应平台", "OPS-F-702", "年度业务连续性演练计划应在每年第一季度完成审批", "关键业务系统、客户服务、支付结算、数据同步和跨部门应急协作", "OPS-BCP-2026-01", "V1.9", "2026年2月8日", "2026-02-15", ["IT-INCIDENT-2026", "PDF-SEC-INFO-2026"], ["关键业务识别与影响分析", "演练计划和场景设计", "应急响应分级", "恢复目标和通讯机制", "复盘整改与证据归档"]),
    ]
    for item in compact_specs:
        filename, doc_id, title, department, process_type, owner, system, form_id, sla, scope, policy_no, version, publish, effective, refs, chapter_names = item
        sections = []
        for idx, chapter in enumerate(chapter_names, 1):
            clauses = [
                f"{chapter}应结合{process_type}的业务目的、风险等级和责任边界执行，不得以口头沟通替代系统记录。",
                f"相关人员应在{system}中留存流程编号、处理意见、附件材料和执行结果，便于后续审计追踪。",
                f"涉及客户、资金、合同、生产系统或外部披露的事项，应由{owner}组织复核并记录例外原因。",
                f"若{chapter}事项与{refs[0]}存在交叉，应先确认主责制度，再补充关联审批意见。",
            ]
            if idx % 2 == 0:
                clauses.append(f"超出常规范围的{process_type}事项，应补充影响范围、临时控制措施和事后复盘安排。")
            sections.append({"title": chapter, "clauses": clauses})
        PDF_SPECS.append(make_base_spec(
            filename=filename, doc_id=doc_id, title=title, department=department, process_type=process_type,
            risk_level="高" if department in {"Security", "Legal", "AI Governance", "Operations"} and "BCP" in doc_id or department in {"Legal", "AI Governance"} else "中",
            owner=owner, system=system, form_id=form_id, approval_sla=sla, scope=scope, policy_no=policy_no,
            version=version, publish_date=publish, effective_date=effective, cross_refs=refs,
            revision_history=[["V1.0", "2025年6月1日", f"首次发布{process_type}基础管理要求。", owner], [version, publish, f"补充{process_type}场景下的审批、例外、留痕和抽查要求。", owner]],
            approval_flow=[{"step": "申请提交", "role": "申请人", "requirement": f"在{system}提交{form_id}及事项说明。", "sla": "T日"}, {"step": "主管确认", "role": "直属主管", "requirement": "确认业务必要性、预算或资源影响。", "sla": "1个工作日"}, {"step": "专业复核", "role": owner, "requirement": "复核材料完整性、制度适用性和风险控制措施。", "sla": sla}, {"step": "执行归档", "role": "执行部门", "requirement": "回填处理结果并归档附件。", "sla": "3个工作日"}],
            sections=sections, page_break_after=[2, 4],
            appendices=[{"title": f"{process_type}材料清单", "widths": [42, 34, 28, 66], "rows": [["材料名称", "提交人", "是否必填", "说明"], [form_id, "申请人", "是", "包含事项背景、影响范围和期望完成时间"], ["审批意见", "直属主管", "是", "确认业务必要性和风险"], ["补充证明", "申请人", "视情况", "高风险或例外事项必须提交"]]}, {"title": f"{process_type}抽查记录表", "widths": [38, 38, 38, 56], "rows": [["抽查项", "检查口径", "结果", "整改要求"], ["材料完整性", "附件是否齐全", "待填写", "缺失材料两个工作日内补齐"], ["审批合规", "是否越级或绕过系统", "待填写", "发现问题需复盘"], ["归档情况", "结果是否回填", "待填写", "完成归档后关闭"]]}],
            material_answer=f"办理{process_type}通常需要提交{form_id}、事项说明、主管审批意见、风险控制材料和执行结果记录。",
            exception_section=chapter_names[-1],
            exception_answer=f"{process_type}遇到紧急或例外情况时，应说明原因、影响范围、临时控制措施和事后补审安排。",
            cross_ref_section=chapter_names[3] if len(chapter_names) > 3 else chapter_names[-1],
        ))


def enrich_specs_for_realistic_depth() -> None:
    notes = {
        "PDF-HR-HANDBOOK-2026": [
            "员工在供应商评审中发现亲属任职关系，应暂停参与评分，并在利益冲突申报表中说明关系、事项和建议回避范围。",
            "员工在客户群内表达未经批准的赔付承诺，主管应先冻结承诺口径，再由客户运营、法务和人力资源共同确认处理方式。",
            "同一违规行为同时涉及考勤造假和客户信息泄露时，应由人力资源部确认纪律处理主线，由信息安全部确认安全事件等级。",
            "员工对纪律处理提出申诉但未提交新证据的，复核重点应放在事实认定和程序合规，而不是重复讨论已确认事实。",
        ],
        "PDF-HR-ATT-2026": [
            "员工因地铁停运导致部门多人迟到，人力资源部可发布统一豁免口径，员工仍应在系统中关联通知编号。",
            "外勤人员在客户现场无法定位打卡时，应补充客户会议邀请、现场照片或项目负责人确认，不得仅提交文字说明。",
            "连续远程办公期间多次未响应会议和协作消息的，主管可要求员工补充工作日志，并重新评估远程办公资格。",
        ],
        "PDF-HR-LEAVE-PDF-2026": [
            "员工年假与关键系统上线冲突时，主管不得直接拒绝休假，应先评估交接、替补和值守方案。",
            "员工突发病假无法事前申请的，可以由同事或主管代为告知，返岗后三个工作日内补齐证明。",
            "婚假、产检假等涉及个人隐私材料的，HRBP 应限定材料查看范围，不得转发至无关群组。",
        ],
        "PDF-FIN-EXP-2026": [
            "同一客户招待被拆分为多张小额报销单时，财务应按同一事项合并判断审批阈值。",
            "员工丢失纸质发票但能提供电子支付记录时，不代表自动可以报销，还需说明无法重开发票的原因。",
            "境外票据的币种、汇率和业务目的应同时说明，财务可要求补充翻译或付款凭证。",
            "预算科目不匹配但业务真实的费用，应先完成预算调整，再进入付款批次。",
        ],
        "PDF-SEC-INFO-2026": [
            "运维人员临时申请生产管理员权限时，应限制到具体系统、具体时间窗口和具体操作事项。",
            "外包人员项目结束但账号仍可访问测试环境的，系统负责人应在权限复核中说明原因并立即回收。",
            "发现异地异常登录后，应先冻结账号，再由员工确认是否本人操作，不能仅依赖密码修改作为闭环。",
        ],
        "PDF-SEC-DATAEXPORT-2026": [
            "业务团队希望将客户明细发给外部咨询机构做分析时，应先评估是否可以改为脱敏汇总数据。",
            "监管报送需要明文客户信息的，应在审批中注明法规依据、接收机构、传输方式和留存期限。",
            "数据已经外发但发现字段范围超出审批，应立即通知接收方停止使用，并启动安全事件评估。",
            "将客户数据输入外部 AI 工具进行摘要分析，视同数据外发和 AI 使用双重高风险场景。",
        ],
        "PDF-PROC-PURCHASE-2026": [
            "采购申请人把同一软件服务拆成多个低金额订单时，采购部应按年度累计金额判断是否触发评审。",
            "紧急采购可以先完成风险评估和临时授权，但不得省略预算、合同和验收材料。",
            "单一来源采购必须说明不可替代性、价格合理性和供应连续性，不得以熟悉供应商作为理由。",
        ],
        "PDF-AI-USAGE-2026": [
            "员工使用 AI 工具生成客户邮件时，应人工复核事实、语气、承诺边界和敏感信息。",
            "研发人员使用 AI 辅助生成代码时，应检查许可证、漏洞风险和是否包含公司源代码片段。",
            "将内部会议纪要输入外部 AI 工具前，应确认文档密级和是否包含客户、财务或未公开战略信息。",
        ],
        "PDF-OPS-BCP-2026": [
            "支付链路故障影响客户下单时，应同时启动技术恢复、客服口径和业务补偿评估。",
            "演练脚本不能只验证系统恢复，还应验证联系人、升级路径、客户通知和人工兜底能力。",
            "复盘发现恢复时间超过目标时，应形成整改清单，并在下一次演练中验证整改效果。",
        ],
    }
    matrices = {
        "PDF-FIN-EXP-2026": [["检查项", "抽查口径", "风险信号", "整改要求"], ["重复票据", "同一发票号码和金额是否重复", "多次提交或拆分提交", "追回款项并记录异常"], ["预算匹配", "费用科目与预算项目是否一致", "频繁改科目或无预算", "补充预算调整记录"], ["逾期报销", "超过三十日是否说明原因", "集中补提历史费用", "部门负责人复核"]],
        "PDF-SEC-DATAEXPORT-2026": [["检查项", "抽查口径", "风险信号", "整改要求"], ["字段范围", "实际导出字段是否超审批", "出现身份信息或明文字段", "立即停止使用并补审"], ["接收方", "接收方是否与审批一致", "个人邮箱或网盘外发", "启动安全事件评估"], ["销毁确认", "是否按期限反馈销毁", "逾期未确认", "暂停后续导出权限"]],
        "PDF-PROC-PURCHASE-2026": [["检查项", "抽查口径", "风险信号", "整改要求"], ["拆单风险", "同类采购是否被拆分", "多笔接近阈值订单", "合并评审并复盘"], ["供应商准入", "是否完成资质和廉洁确认", "先采购后准入", "暂停付款并补齐材料"], ["验收记录", "是否有交付证明", "验收人与申请人重合", "追加独立验收"]],
        "PDF-HR-HANDBOOK-2026": [["检查项", "抽查口径", "风险信号", "整改要求"], ["利益冲突", "是否主动申报关联关系", "供应商或候选人关系未披露", "补充申报并回避"], ["纪律程序", "是否保留事实和陈述", "仅凭口头结论处理", "补齐证据和复核"], ["专项衔接", "是否适用正确制度", "通用手册替代专项制度", "重新确认主责制度"]],
    }
    for spec in PDF_SPECS:
        if spec["doc_id"] in notes:
            spec["case_notes"] = notes[spec["doc_id"]]
        if spec["doc_id"] in matrices:
            spec["control_matrix"] = matrices[spec["doc_id"]]


def main() -> None:
    extend_specs_with_domain_documents()
    add_remaining_specs()
    add_compact_specs()
    enrich_specs_for_realistic_depth()
    clean_output_dir()
    styles = make_styles()
    for spec in PDF_SPECS:
        generate_pdf(spec, styles)

    PDF_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PDF_EVAL_PATH.open("w", encoding="utf-8") as handle:
        total = 0
        for spec in PDF_SPECS:
            for case in eval_cases_for(spec):
                handle.write(json.dumps(case, ensure_ascii=False) + "\n")
                total += 1
        for case in [
            {
                "id": "pdf_out_of_scope_stock_purchase",
                "question": "公司股票现在适合买入吗？",
                "expected_doc_ids": [],
                "expected_sections": [],
                "reference_answer": "知识库不包含股票投资建议，应拒答并建议咨询专业投资顾问。",
                "question_type": "PDF-拒答型",
                "department": "General",
                "should_refuse": True,
            },
            {
                "id": "pdf_out_of_scope_personal_tax",
                "question": "我个人房贷利息怎么抵扣个税？",
                "expected_doc_ids": [],
                "expected_sections": [],
                "reference_answer": "知识库不包含个人税务筹划，应拒答并建议咨询税务专业人士。",
                "question_type": "PDF-拒答型",
                "department": "General",
                "should_refuse": True,
            },
        ]:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")
            total += 1

    print(f"generated_pdf_policies={len(PDF_SPECS)}")
    print(f"generated_pdf_eval_cases={total}")


if __name__ == "__main__":
    main()
