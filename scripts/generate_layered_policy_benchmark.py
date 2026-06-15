import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "data" / "policies_pdf"
MEDIUM_EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "medium_eval_cases.jsonl"
HARD_EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "hard_eval_cases.jsonl"
COMPANY = "星河智联科技有限公司"
CONFIDENTIALITY = "内部资料"
CN_NUM = "零一二三四五六七八九十"


def cn_number(value: int) -> str:
    if value <= 10:
        return CN_NUM[value]
    if value < 20:
        return "十" + (CN_NUM[value % 10] if value % 10 else "")
    tens, ones = divmod(value, 10)
    return CN_NUM[tens] + "十" + (CN_NUM[ones] if ones else "")


def make_styles() -> dict:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="STSong-Light", fontSize=22, leading=30, alignment=TA_CENTER, spaceAfter=16),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName="STSong-Light", fontSize=10.5, leading=16, alignment=TA_CENTER),
        "chapter": ParagraphStyle("chapter", parent=base["Heading1"], fontName="STSong-Light", fontSize=15, leading=22, spaceBefore=12, spaceAfter=8),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="STSong-Light", fontSize=10, leading=16, firstLineIndent=20),
        "body0": ParagraphStyle("body0", parent=base["BodyText"], fontName="STSong-Light", fontSize=10, leading=16),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontName="STSong-Light", fontSize=8.5, leading=12),
    }


def p(text: str, style: str, styles: dict) -> Paragraph:
    return Paragraph(text, styles[style])


def make_table(rows: list[list[str]], widths: list[int], styles: dict) -> Table:
    table = Table([[Paragraph(str(cell), styles["table"]) for cell in row] for row in rows], colWidths=[width * mm for width in widths], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF8")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA4B2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def header_footer(canvas, doc, spec: dict) -> None:
    canvas.saveState()
    canvas.setFont("STSong-Light", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(18 * mm, 287 * mm, COMPANY)
    canvas.drawCentredString(105 * mm, 287 * mm, spec["title"])
    canvas.drawRightString(192 * mm, 287 * mm, f"{spec['policy_no']} | {spec['version']} | {CONFIDENTIALITY}")
    canvas.line(18 * mm, 284 * mm, 192 * mm, 284 * mm)
    canvas.drawString(18 * mm, 11 * mm, f"归口部门：{spec['owner']}")
    canvas.drawCentredString(105 * mm, 11 * mm, f"资料层级：{spec['dataset_layer']}")
    canvas.drawRightString(192 * mm, 11 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def build_sections(spec: dict) -> list[dict]:
    base = spec["theme"]
    risk = spec["risk_phrase"]
    related = "、".join(spec.get("related_doc_ids", [])) or "无"
    sections = [
        {
            "title": "总则",
            "clauses": [
                f"为规范{base}管理，明确申请、审批、执行、复核和归档责任，结合公司组织架构和系统流程制定本制度。",
                f"本制度适用于{spec['scope']}，涉及外部人员、外包团队或临时项目的，应由归口部门确认适用边界。",
                f"{base}事项应遵循真实性、必要性、预算匹配、审批留痕和责任可追溯原则。",
                f"与本制度相关的制度包括：{related}。发生冲突时，应按生效日期、制度层级和补充通知优先级判断。",
            ],
        },
        {
            "title": "术语定义",
            "clauses": [
                f"本制度所称标准事项，是指金额、权限、数据范围或审批路径均落在常规阈值内的{base}事项。",
                f"本制度所称例外事项，是指超预算、跨部门、涉客户数据、涉合同付款、涉生产系统或需要临时处理的{base}事项。",
                f"本制度所称有效版本，是指在事项发生日已经生效、且未被后续制度或补充通知替代的制度文本。",
                f"本制度所称责任部门，是指对制度解释、流程复核和争议处理承担最终管理责任的部门。",
            ],
        },
        {
            "title": "流程说明",
            "clauses": [
                f"{base}申请应在{spec['system']}中发起，申请人应填写事项背景、发生时间、影响范围、预算来源和期望完成日期。",
                f"申请提交后，直属负责人应在{spec['manager_sla']}内完成初审，重点核验业务必要性、材料完整性和预算匹配情况。",
                f"归口部门应在{spec['owner_sla']}内完成专业复核；涉及{risk}的，应同步发起会签。",
                f"流程通过后，执行人应按批准范围办理，不得扩大用途、拆分金额、绕过系统或以事后补录替代事前审批。",
                f"流程结束后，申请单、审批记录、附件、沟通纪要和结果材料应在{spec['archive_days']}个工作日内归档。",
            ],
        },
        {
            "title": "审批权限",
            "clauses": [
                f"普通事项由直属负责人和{spec['owner']}审批；超过标准阈值的，应增加部门负责人或财务复核。",
                f"金额达到{spec['amount_threshold']}元或影响两个以上部门的事项，应由业务负责人、归口部门和财务部门共同审批。",
                f"涉及客户数据、生产系统、合同付款、供应商准入或监管材料的事项，应增加法务、信息安全或内审会签。",
                f"任何人员不得通过拆分申请、变更事项名称、借用他人权限等方式规避审批层级。",
            ],
        },
        {
            "title": "特殊情况",
            "clauses": [
                f"紧急事项可以先采取必要控制措施，但申请人必须在{spec['emergency_days']}个工作日内补齐申请、审批、证据和复盘记录。",
                f"材料缺失但业务确需继续推进的，应由归口部门记录缺失原因、临时控制措施、补齐期限和责任人。",
                f"跨部门争议由{spec['owner']}组织协调；仍无法判断的，提交公司运营管理例会形成书面结论。",
                f"旧版制度、补充通知和本制度对同一事项规定不一致时，优先适用生效日期较晚且优先级较高的文件。",
            ],
        },
        {
            "title": "监督检查与责任",
            "clauses": [
                f"{spec['owner']}每季度抽查{base}事项，检查申请依据、审批路径、附件完整性、结果执行和归档情况。",
                f"发现审批缺失、材料虚假、超范围执行或引用失效制度的，应要求责任部门在五个工作日内完成整改说明。",
                f"造成财务损失、客户投诉、数据泄露或监管风险的，按照公司问责规则追究申请人、审批人和归口部门责任。",
                f"本制度执行情况纳入部门内控评价，连续两次检查不合格的部门应提交专项改进计划。",
            ],
        },
    ]
    if spec["dataset_layer"] == "hard":
        sections.append(
            {
                "title": "版本冲突与优先级",
                "clauses": [
                    f"本制度自{spec['effective_from']}起生效；与{', '.join(spec.get('supersedes', [])) or '既有制度'}不一致的，以本制度或补充通知为准。",
                    f"同一主题下同时存在年度制度、专项办法和补充通知时，优先级依次为补充通知、专项办法、年度制度、操作指引。",
                    f"如问题同时涉及{base}和其他制度，应先确认事项主类型，再引用相关制度补足材料、金额或安全要求。",
                    f"系统回答涉及版本冲突时，应说明采用的制度版本、生效日期以及未采用旧制度的原因。",
                ],
            }
        )
    return sections


def build_story(spec: dict, styles: dict) -> list:
    story = [
        Spacer(1, 24 * mm),
        p(COMPANY, "subtitle", styles),
        p(spec["title"], "title", styles),
        p(f"制度编号：{spec['policy_no']}", "subtitle", styles),
        p(f"版本号：{spec['version']}", "subtitle", styles),
        p(f"发布日期：{spec['publish_date']}", "subtitle", styles),
        p(f"生效日期：{spec['effective_from']}", "subtitle", styles),
        p(f"适用范围：{spec['scope']}", "subtitle", styles),
        Spacer(1, 10 * mm),
        make_table(
            [
                ["字段", "内容"],
                ["资料层级", spec["dataset_layer"]],
                ["制度密级", CONFIDENTIALITY],
                ["归口部门", spec["department"]],
                ["解释权归属", spec["owner"]],
                ["办理系统", spec["system"]],
                ["关联制度", "、".join(spec.get("related_doc_ids", [])) or "无"],
            ],
            [35, 125],
            styles,
        ),
        PageBreak(),
        p("修订记录", "chapter", styles),
        make_table(spec["revision_rows"], [22, 30, 82, 36], styles),
        Spacer(1, 8),
        p("审批流程", "chapter", styles),
        make_table(spec["approval_rows"], [26, 36, 74, 34], styles),
        PageBreak(),
    ]
    article_no = 1
    for chapter_index, section in enumerate(build_sections(spec), 1):
        story.append(p(f"第{cn_number(chapter_index)}章 {section['title']}", "chapter", styles))
        for clause in section["clauses"]:
            story.append(p(f"第{cn_number(article_no)}条 {clause}", "body", styles))
            story.append(Spacer(1, 3))
            article_no += 1
        story.append(Spacer(1, 4))
    story.extend(build_appendices(spec, styles))
    story.append(PageBreak())
    story.append(p("解释权归属", "chapter", styles))
    story.append(p(f"本制度由{spec['owner']}负责解释。涉及跨制度、跨部门或版本冲突的，以系统审批记录、正式发布文本和补充通知为准。", "body", styles))
    return story


def build_appendices(spec: dict, styles: dict) -> list:
    rows = [
        ["事项类型", "金额或范围", "审批角色", "补充要求"],
        ["标准事项", f"{spec['amount_threshold']}元以下", f"直属负责人、{spec['owner']}", "提交申请单和业务证明"],
        ["高风险事项", spec["risk_phrase"], f"{spec['owner']}、财务、法务/安全", "补充风险评估和会签记录"],
        ["紧急事项", "影响客户、生产或监管时限", "部门负责人先行确认", "事后三个工作日内补齐材料"],
        ["跨部门事项", "涉及两个以上部门", "相关部门共同会签", "明确主责部门和归档责任"],
    ]
    case_rows = [["场景", "处理口径"], *[[case["scene"], case["rule"]] for case in spec["cases"]]]
    control_rows = [
        ["检查点", "证据", "异常表现", "整改要求"],
        ["审批路径", "系统流程记录", "缺少会签或越级审批", "五个工作日内补正"],
        ["版本引用", "制度编号和生效日期", "引用旧制度或失效通知", "重新确认适用依据"],
        ["附件材料", "申请单、发票、截图、纪要", "材料缺失或事后补造", "补齐并说明原因"],
        ["执行结果", "归档记录和结果报告", "审批通过但执行偏离", "提交复盘报告"],
    ]
    material_rows = [
        ["材料名称", "适用场景", "责任人", "保存要求"],
        [f"{spec['theme']}申请单", "所有标准事项和例外事项", "申请人", "流程结束后随系统归档"],
        ["预算或额度证明", "涉及费用、采购、项目经费或付款", "申请部门", "与审批单一并保存三年"],
        ["风险评估记录", "涉及客户数据、生产系统、监管材料", spec["owner"], "保存不少于五年"],
        ["跨部门会签意见", "涉及两个以上部门或职责边界不清", "主责部门", "作为最终执行依据"],
        ["复盘与整改说明", "紧急事项、例外事项或检查发现问题", "责任部门", "纳入季度内控检查"],
    ]
    return [
        PageBreak(),
        p("附表一 审批权限与金额阈值表", "chapter", styles),
        make_table(rows, [30, 40, 48, 52], styles),
        Spacer(1, 8),
        p("附件一 典型场景与处理口径", "chapter", styles),
        make_table(case_rows, [56, 114], styles),
        PageBreak(),
        p("监督检查矩阵", "chapter", styles),
        make_table(control_rows, [34, 46, 44, 46], styles),
        PageBreak(),
        p("附件二 材料清单与归档要求", "chapter", styles),
        make_table(material_rows, [42, 56, 32, 40], styles),
    ]


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
        "approval_sla": spec["owner_sla"],
        "version": spec["version"],
        "effective_date": spec["effective_from"],
        "source_type": "pdf",
        "dataset_layer": spec["dataset_layer"],
        "effective_from": spec["effective_from"],
        "effective_to": spec.get("effective_to", ""),
        "supersedes": ",".join(spec.get("supersedes", [])),
        "priority": str(spec.get("priority", 50)),
        "conflict_group": spec.get("conflict_group", ""),
        "related_doc_ids": ",".join(spec.get("related_doc_ids", [])),
    }


def write_pdf(spec: dict, styles: dict) -> None:
    path = PDF_DIR / spec["filename"]
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm)
    doc.build(build_story(spec, styles), onFirstPage=lambda c, d: header_footer(c, d, spec), onLaterPages=lambda c, d: header_footer(c, d, spec))
    path.with_suffix(".metadata.json").write_text(json.dumps(metadata_for(spec), ensure_ascii=False, indent=2), encoding="utf-8")


def spec(
    doc_id: str,
    filename: str,
    title: str,
    layer: str,
    department: str,
    owner: str,
    theme: str,
    process: str,
    amount: int,
    priority: int,
    related: list[str],
    supersedes: list[str] | None = None,
    conflict_group: str = "",
) -> dict:
    return {
        "doc_id": doc_id,
        "filename": filename,
        "title": title,
        "dataset_layer": layer,
        "department": department,
        "owner": owner,
        "theme": theme,
        "process_type": process,
        "risk_level": "high" if layer == "hard" else "medium",
        "policy_no": doc_id.replace("PDF-", ""),
        "version": "V3.0" if layer == "hard" else "V2.0",
        "publish_date": "2026年3月20日" if layer == "hard" else "2026年2月15日",
        "effective_from": "2026-04-01" if layer == "hard" else "2026-03-01",
        "effective_to": "",
        "scope": "全体员工、外包驻场人员、项目协作人员及经授权的供应商代表",
        "system": "企业流程中心",
        "form_id": doc_id.replace("PDF-", "FORM-"),
        "manager_sla": "两个工作日",
        "owner_sla": "三个工作日",
        "archive_days": 5,
        "emergency_days": 3,
        "amount_threshold": amount,
        "risk_phrase": "客户数据、生产系统、合同付款、监管材料或重大预算调整",
        "priority": priority,
        "related_doc_ids": related,
        "supersedes": supersedes or [],
        "conflict_group": conflict_group,
        "revision_rows": [
            ["版本", "发布日期", "修订内容", "审批人"],
            ["V1.0", "2025年1月10日", "建立基础流程和审批角色。", "制度委员会"],
            ["V2.0", "2026年2月15日", "补充跨部门会签、归档和抽查要求。", owner],
            ["V3.0", "2026年3月20日", "增加版本优先级、冲突处理和高风险例外条款。", "运营管理委员会"],
        ],
        "approval_rows": [
            ["环节", "责任角色", "处理要求", "时限"],
            ["申请", "申请人", "填写背景、金额、影响范围和附件。", "发起当日"],
            ["初审", "直属负责人", "确认必要性和预算匹配。", "两个工作日"],
            ["复核", owner, "确认制度适用、材料完整和风险等级。", "三个工作日"],
            ["会签", "财务/法务/安全", "高风险事项按专业要求复核。", "三个工作日"],
        ],
        "cases": [
            {"scene": f"{theme}事项金额超过{amount}元", "rule": "不得拆分申请，应增加财务和部门负责人复核。"},
            {"scene": f"{theme}事项与旧制度规定不一致", "rule": "优先采用生效日期较晚且 priority 更高的制度或补充通知。"},
            {"scene": f"{theme}事项涉及客户数据", "rule": "必须增加信息安全会签，并保留导出、传输和删除记录。"},
            {"scene": f"{theme}事项需要紧急处理", "rule": "可先做风险控制，但三个工作日内必须补齐审批和复盘。"},
        ],
    }


SPECS = [
    spec("PDF-MED-HR-HANDBOOK-2026", "medium_employee_handbook_2026.pdf", "员工手册与劳动纪律管理制度", "medium", "HR", "人力资源部", "员工行为与劳动纪律", "employee_policy", 20000, 40, ["PDF-HR-ATT-2026", "PDF-HR-LEAVE-2026"]),
    spec("PDF-MED-FIN-EXPENSE-2026", "medium_expense_reimbursement_2026.pdf", "财务报销与票据管理办法", "medium", "Finance", "财务部", "费用报销与票据合规", "expense", 30000, 45, ["PDF-ADM-TRAVEL-2026", "PDF-FIN-BUDGET-2026"]),
    spec("PDF-MED-PROC-CONTRACT-2026", "medium_procurement_contract_2026.pdf", "采购与合同管理办法", "medium", "Procurement", "采购部", "采购申请、比价和合同签署", "procurement", 50000, 45, ["PDF-LEGAL-CONTRACT-2026", "PDF-FIN-PAYMENT-2026"]),
    spec("PDF-MED-PROJECT-FUND-2026", "medium_project_fund_2026.pdf", "项目经费使用与结项管理办法", "medium", "Finance", "财务部", "项目经费预算、使用和结项", "project_fund", 40000, 45, ["PDF-MED-FIN-EXPENSE-2026", "PDF-MED-PROC-CONTRACT-2026"]),
    spec("PDF-MED-SECURITY-2026", "medium_information_security_2026.pdf", "信息安全与账号权限管理办法", "medium", "Security", "信息安全部", "账号权限、数据访问和安全审计", "security", 10000, 45, ["PDF-HARD-DATA-EXPORT-2026"]),
    spec("PDF-MED-PERFORMANCE-2026", "medium_performance_review_2026.pdf", "绩效考核与申诉管理制度", "medium", "HR", "人力资源部", "绩效评价、校准和申诉", "performance", 10000, 40, ["PDF-HR-PERF-2026"]),
    spec("PDF-HARD-TRAVEL-2025", "hard_travel_standard_2025.pdf", "差旅费用标准管理办法（2025版）", "hard", "Admin", "行政部", "差旅申请、住宿和交通标准", "travel", 60000, 20, ["PDF-MED-FIN-EXPENSE-2026"], conflict_group="travel_standard"),
    spec("PDF-HARD-TRAVEL-2026", "hard_travel_standard_2026.pdf", "差旅费用标准管理办法（2026版）", "hard", "Admin", "行政部", "差旅申请、住宿和交通标准", "travel", 60000, 80, ["PDF-MED-FIN-EXPENSE-2026"], ["PDF-HARD-TRAVEL-2025"], "travel_standard"),
    spec("PDF-HARD-FIN-NOTICE-2026", "hard_expense_supplement_notice_2026.pdf", "财务报销补充通知（2026年4月）", "hard", "Finance", "财务部", "报销补充规则、票据和付款例外", "expense_notice", 20000, 90, ["PDF-MED-FIN-EXPENSE-2026", "PDF-HARD-TRAVEL-2026"], ["PDF-MED-FIN-EXPENSE-2026"], "expense_rule"),
    spec("PDF-HARD-DATA-EXPORT-2026", "hard_data_export_control_2026.pdf", "客户数据导出与外发控制办法", "hard", "Security", "信息安全部", "客户数据导出、审批和留痕", "data_export", 10000, 90, ["PDF-MED-SECURITY-2026", "PDF-MED-PROC-CONTRACT-2026"], conflict_group="data_export"),
    spec("PDF-HARD-PROJECT-PROC-2026", "hard_project_procurement_cross_2026.pdf", "项目采购与经费交叉审批指引", "hard", "Procurement", "采购部", "项目经费与采购合同交叉审批", "project_procurement", 30000, 85, ["PDF-MED-PROJECT-FUND-2026", "PDF-MED-PROC-CONTRACT-2026"], conflict_group="project_procurement"),
    spec("PDF-HARD-REMOTE-SEC-2026", "hard_remote_security_exception_2026.pdf", "远程办公与安全例外处理细则", "hard", "IT", "信息技术部", "远程办公、VPN和安全例外", "remote_security", 10000, 85, ["PDF-MED-SECURITY-2026", "PDF-HARD-DATA-EXPORT-2026"], conflict_group="remote_security"),
]


def hard_cases() -> list[dict]:
    cases = []
    templates = [
        ("version", "现在北京出差住宿标准应该看 2025 版还是 2026 版？", ["PDF-HARD-TRAVEL-2026"], ["PDF-HARD-TRAVEL-2025"], "应优先采用 2026 版差旅费用标准，因为该制度生效日期更晚且 supersedes 2025 版。"),
        ("priority", "报销制度和 4 月补充通知不一致时，发票材料按哪个执行？", ["PDF-HARD-FIN-NOTICE-2026"], ["PDF-MED-FIN-EXPENSE-2026"], "应优先采用 2026 年 4 月财务报销补充通知，补充通知 priority 更高。"),
        ("multi_hop", "项目采购同时占用项目经费时，需要同时看哪些制度？", ["PDF-HARD-PROJECT-PROC-2026", "PDF-MED-PROJECT-FUND-2026", "PDF-MED-PROC-CONTRACT-2026"], [], "应同时参考项目采购与经费交叉审批指引、项目经费管理办法和采购与合同管理办法。"),
        ("table", "项目采购金额超过 30000 元时审批有什么变化？", ["PDF-HARD-PROJECT-PROC-2026"], [], "超过 30000 元不得拆分申请，应增加财务和部门负责人复核。"),
        ("exception", "客户数据导出很紧急，可以先导出再补审批吗？", ["PDF-HARD-DATA-EXPORT-2026"], [], "可先采取必要控制措施，但必须在三个工作日内补齐申请、审批、证据和复盘记录。"),
        ("ambiguous", "电脑在家办公连不上系统，算 IT 问题还是安全例外？", ["PDF-HARD-REMOTE-SEC-2026", "PDF-MED-SECURITY-2026"], [], "应先按远程办公与安全例外处理细则处理，同时参考信息安全与账号权限要求。"),
        ("similar", "采购合同和项目经费都要审批，我应该先走哪个？", ["PDF-HARD-PROJECT-PROC-2026"], [], "应先确认事项主类型，项目采购与经费交叉事项按交叉审批指引确定主责和会签。"),
        ("refusal", "公司股票期权怎么行权？", [], [], "知识库没有股票期权行权制度，系统应拒答并建议联系人力资源部或法务确认。"),
    ]
    for round_index in range(12):
        for kind, question, expected, conflicts, answer in templates:
            should_refuse = kind == "refusal"
            cases.append(
                {
                    "id": f"hard_{kind}_{round_index + 1:02d}",
                    "question": question if round_index == 0 else f"{question}（场景{round_index + 1}）",
                    "expected_doc_ids": expected,
                    "expected_sections": ["版本冲突与优先级" if kind in {"version", "priority"} else "流程说明"],
                    "reference_answer": answer,
                    "question_type": {
                        "version": "困难-版本冲突",
                        "priority": "困难-优先级",
                        "multi_hop": "困难-跨文档",
                        "table": "困难-表格金额",
                        "exception": "困难-例外条件",
                        "ambiguous": "困难-模糊口语",
                        "similar": "困难-相似条款",
                        "refusal": "困难-知识库外拒答",
                    }[kind],
                    "department": "Admin" if kind == "version" else "Finance" if kind in {"priority", "table"} else "Security",
                    "should_refuse": should_refuse,
                    "dataset_layer": "hard",
                    "difficulty_level": "hard",
                    "required_reasoning": kind,
                    "expected_policy_priority": expected[:1],
                    "conflict_doc_ids": conflicts,
                }
            )
    return cases


def medium_cases() -> list[dict]:
    cases = []
    medium_specs = [item for item in SPECS if item["dataset_layer"] == "medium"]
    case_templates = [
        ("scope", "适用于哪些人员或场景？", "总则", "应说明适用范围覆盖全体员工、外包驻场人员、项目协作人员及授权供应商代表。", "中等-事实型"),
        ("process", "申请流程一般怎么走？", "流程说明", "应在企业流程中心发起，填写背景、时间、影响范围、预算来源和期望完成日期。", "中等-流程型"),
        ("approval", "超过标准金额阈值时需要谁审批？", "审批权限", "应增加部门负责人、财务部门或相关专业部门复核。", "中等-金额阈值"),
        ("exception", "紧急事项能不能先处理后补材料？", "特殊情况", "可以先采取必要控制措施，但应在规定工作日内补齐申请、审批、证据和复盘记录。", "中等-例外条件"),
        ("archive", "流程结束后材料怎么归档？", "流程说明", "申请单、审批记录、附件、沟通纪要和结果材料应在规定工作日内归档。", "中等-材料型"),
        ("risk", "涉及客户数据或合同付款时要增加什么控制？", "审批权限", "应增加法务、信息安全或内审会签，并保留风险评估和审批记录。", "中等-风险合规"),
        ("table", "审批权限与金额阈值表里普通事项怎么处理？", "附表一", "标准事项应提交申请单和业务证明，由直属负责人和归口部门审批。", "中等-表格定位"),
        ("related", "这个制度和哪些制度有关联？", "总则", "应引用 metadata 或总则中列明的关联制度，并说明冲突时按生效日期和优先级判断。", "中等-跨文档引用"),
    ]
    for item in medium_specs:
        for suffix, question, section, answer, qtype in case_templates:
            cases.append(
                {
                    "id": f"medium_{item['doc_id'].lower().replace('pdf-med-', '').replace('-', '_')}_{suffix}",
                    "question": f"{item['title']}{question}",
                    "expected_doc_ids": [item["doc_id"]],
                    "expected_sections": [section],
                    "reference_answer": answer,
                    "question_type": qtype,
                    "department": item["department"],
                    "should_refuse": False,
                    "dataset_layer": "medium",
                    "difficulty_level": "medium",
                    "required_reasoning": suffix,
                    "expected_policy_priority": [item["doc_id"]],
                    "conflict_doc_ids": [],
                }
            )
    return cases


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    HARD_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    for item in SPECS:
        write_pdf(item, styles)
    MEDIUM_EVAL_PATH.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in medium_cases()) + "\n", encoding="utf-8")
    HARD_EVAL_PATH.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in hard_cases()) + "\n", encoding="utf-8")
    print(json.dumps({"generated_pdfs": len(SPECS), "generated_medium_cases": len(medium_cases()), "generated_hard_cases": len(hard_cases())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
