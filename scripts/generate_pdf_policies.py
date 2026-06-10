import json
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "data" / "policies_pdf"
PDF_EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "pdf_eval_cases.jsonl"
COMPANY_NAME = "星河智联科技有限公司"


BASE_ARTICLES = [
    "第一条 为规范{process_type}管理，统一执行口径，维护公司运营秩序，根据公司治理要求和相关业务规范，制定本制度。",
    "第二条 本制度适用于{scope}。外包人员、实习生和临时协作人员涉及本制度事项的，参照本制度执行。",
    "第三条 申请人应保证提交材料真实、完整、及时，不得以口头确认、即时通讯截图或个人邮件替代系统审批记录。",
    "第四条 主管负责人应对业务必要性、资源占用、风险影响和执行结果进行确认，并对审批意见承担管理责任。",
    "第五条 涉及客户数据、财务资金、生产系统、合同承诺、外部披露或监管报送的事项，应同步留存审批、复核和执行证据。",
    "第六条 标准办理时限为：{approval_sla}。材料缺失、信息错误或审批链路变更的，自材料补齐或流程重新提交后重新计算时限。",
    "第七条 高风险或跨部门事项应由{owner}组织复核，必要时邀请法务、信息安全、财务、人力资源或内审部门共同确认。",
    "第八条 紧急事项可以启动例外流程，但申请人必须说明紧急原因、临时控制措施、影响范围和事后补审计划。",
    "第九条 执行部门应在流程办结后三个工作日内回填处理结果，并将相关材料归档至{system}或指定档案库。",
    "第十条 本制度由{owner}负责解释；与既有专项制度不一致的，以最新发布且适用范围更具体的制度为准。",
]


PDF_SPECS = [
    {
        "filename": "employee_handbook_2026.pdf",
        "doc_id": "PDF-HR-HANDBOOK-2026",
        "title": "员工手册",
        "department": "HR",
        "process_type": "员工管理",
        "risk_level": "中",
        "owner": "人力资源部",
        "system": "员工服务系统",
        "form_id": "HR-F-000",
        "approval_sla": "员工手册争议解释应在五个工作日内反馈",
        "scope": "全体正式员工、试用期员工、实习生及签署公司管理协议的外部协作人员",
        "policy_no": "HR-HANDBOOK-2026-01",
        "version": "V3.0",
        "publish_date": "2026年1月5日",
        "effective_date": "2026-02-01",
        "keywords": ["行为规范", "奖惩", "跨制度引用"],
        "cross_refs": ["HR-ATT-2026", "HR-LEAVE-PDF-2026", "SEC-INFO-PDF-2026"],
        "special_rules": [
            "员工违反信息安全制度造成客户数据泄露的，除按本手册处理外，还应按《信息安全与账号权限管理制度》追究责任。",
            "涉及考勤、休假、绩效、报销的专项问题，应优先适用对应专项制度；专项制度未覆盖的，适用本手册通用条款。",
        ],
    },
    {
        "filename": "attendance_policy_2026.pdf",
        "doc_id": "PDF-HR-ATT-2026",
        "title": "员工考勤管理制度",
        "department": "HR",
        "process_type": "考勤管理",
        "risk_level": "中",
        "owner": "人力资源部",
        "system": "员工服务系统",
        "form_id": "HR-F-101",
        "approval_sla": "考勤异常申诉应在三个工作日内提交",
        "scope": "全体正式员工、试用期员工、实习生",
        "policy_no": "HR-ATT-2026-01",
        "version": "V2.1",
        "publish_date": "2026年1月10日",
        "effective_date": "2026-02-01",
        "keywords": ["迟到", "打卡", "弹性工时"],
        "cross_refs": ["HR-LEAVE-PDF-2026", "PDF-HR-HANDBOOK-2026"],
        "special_rules": [
            "2026年2月1日起，研发、产品、数据分析岗位可适用三十分钟弹性到岗窗口，但每日标准工作时长不得减少。",
            "月度迟到三次以内且单次不超过十分钟的，记录为提醒；超过三次或单次超过三十分钟的，应提交异常说明并由直属主管确认。",
        ],
    },
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
        "scope": "全体正式员工、试用期员工、实习生",
        "policy_no": "HR-LEAVE-2026-02",
        "version": "V2.0",
        "publish_date": "2026年1月12日",
        "effective_date": "2026-02-01",
        "keywords": ["年假", "病假", "婚假", "试用期"],
        "cross_refs": ["PDF-HR-ATT-2026"],
        "special_rules": [
            "正式员工连续服务满一年后享有年假；试用期员工原则上不安排年假，确需休假的按事假处理。",
            "病假应上传医疗机构证明，连续病假超过三日的，应补充诊断证明或复诊记录。",
        ],
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
        "scope": "因公产生差旅、招待、办公采购、培训会议等费用的员工",
        "policy_no": "FIN-EXP-2026-01",
        "version": "V3.2",
        "publish_date": "2026年1月15日",
        "effective_date": "2026-02-01",
        "keywords": ["金额阈值", "发票", "预算"],
        "cross_refs": ["FIN-BUDGET-2026", "ADM-TRAVEL-2026"],
        "special_rules": [
            "单笔招待费用超过五千元或单次差旅费用超过两万元的，应在报销前完成预算确认。",
            "电子发票应保证抬头、税号、金额、日期和消费事项一致；不得重复提交同一票据。",
        ],
    },
    {
        "filename": "information_security_2026.pdf",
        "doc_id": "PDF-SEC-INFO-2026",
        "title": "信息安全与账号权限管理制度",
        "department": "Security",
        "process_type": "账号权限",
        "risk_level": "高",
        "owner": "信息安全部",
        "system": "权限管理平台",
        "form_id": "SEC-F-301",
        "approval_sla": "高权限账号申请须至少提前两个工作日提交",
        "scope": "所有使用公司系统、网络、数据和账号权限的人员",
        "policy_no": "SEC-INFO-2026-01",
        "version": "V2.4",
        "publish_date": "2026年1月18日",
        "effective_date": "2026-02-01",
        "keywords": ["账号", "权限", "客户数据"],
        "cross_refs": ["PDF-SEC-DATAEXPORT-2026", "IT-PERM-2026"],
        "special_rules": [
            "生产系统、客户数据、财务数据和管理员权限属于高风险权限，必须按最小权限原则审批。",
            "共享账号原则上禁止使用；因系统限制确需使用的，应指定责任人并开启操作日志审计。",
        ],
    },
    {
        "filename": "performance_review_2026.pdf",
        "doc_id": "PDF-HR-PERF-2026",
        "title": "绩效考核与申诉管理办法",
        "department": "HR",
        "process_type": "绩效考核",
        "risk_level": "中",
        "owner": "人力资源部",
        "system": "绩效管理系统",
        "form_id": "HR-F-103",
        "approval_sla": "绩效申诉应在结果发布后五个工作日内提交",
        "scope": "纳入季度或年度绩效考核的正式员工和试用期员工",
        "policy_no": "HR-PERF-2026-01",
        "version": "V2.2",
        "publish_date": "2026年1月20日",
        "effective_date": "2026-02-01",
        "keywords": ["评分", "申诉", "周期"],
        "cross_refs": ["PDF-HR-HANDBOOK-2026"],
        "special_rules": [
            "绩效评分采用目标达成、行为表现、协作反馈和风险合规四类维度。",
            "员工对评分存在异议的，应先与直属主管沟通，仍无法达成一致的，可提交绩效申诉。",
        ],
    },
    {
        "filename": "onboarding_offboarding_2026.pdf",
        "doc_id": "PDF-HR-ONOFF-2026",
        "title": "员工入离职流程说明",
        "department": "HR",
        "process_type": "入离职流程",
        "risk_level": "中",
        "owner": "人力资源部与信息技术部",
        "system": "员工服务系统",
        "form_id": "HR-F-104",
        "approval_sla": "入职账号应在入职日前两个工作日完成预开通",
        "scope": "正式员工、试用期员工、实习生和外包驻场人员",
        "policy_no": "HR-ONOFF-2026-01",
        "version": "V1.8",
        "publish_date": "2026年1月22日",
        "effective_date": "2026-02-01",
        "keywords": ["入职", "离职", "权限关闭"],
        "cross_refs": ["PDF-SEC-INFO-2026", "IT-ASSET-2026"],
        "special_rules": [
            "离职员工的系统权限应在离职当天关闭，涉密岗位应提前完成资料交接和设备检查。",
            "未完成交接的离职流程不得直接关闭，应由直属主管说明风险并确定补救负责人。",
        ],
    },
    {
        "filename": "remote_work_policy_2026.pdf",
        "doc_id": "PDF-HR-REMOTE-2026",
        "title": "远程办公与异地协作管理规范",
        "department": "HR",
        "process_type": "远程办公",
        "risk_level": "中",
        "owner": "人力资源部与信息安全部",
        "system": "员工服务系统",
        "form_id": "HR-F-105",
        "approval_sla": "连续远程办公超过三天须至少提前两个工作日提交申请",
        "scope": "居家办公、异地办公、跨城市协作、临时远程接入和外部网络使用",
        "policy_no": "HR-REMOTE-2026-01",
        "version": "V2.0",
        "publish_date": "2026年1月25日",
        "effective_date": "2026-02-01",
        "keywords": ["远程办公", "VPN", "异地协作"],
        "cross_refs": ["PDF-SEC-INFO-2026"],
        "special_rules": [
            "远程办公期间不得在公共网络环境处理客户敏感数据，确需处理的应通过公司 VPN 和受控终端访问。",
            "跨境远程办公应额外经过信息安全部和法务部确认，不得自行复制客户数据至境外设备。",
        ],
    },
    {
        "filename": "open_source_compliance_2026.pdf",
        "doc_id": "PDF-IT-OSS-2026",
        "title": "开源软件引入与许可证合规规范",
        "department": "IT",
        "process_type": "开源合规",
        "risk_level": "高",
        "owner": "技术委员会与法务部",
        "system": "研发资产管理平台",
        "form_id": "IT-F-401",
        "approval_sla": "引入 GPL/AGPL 类许可证组件须在上线前五个工作日完成法务复核",
        "scope": "开源组件选型、许可证审查、漏洞扫描、版本升级、二次分发和开源义务履行",
        "policy_no": "IT-OSS-2026-01",
        "version": "V2.3",
        "publish_date": "2026年1月26日",
        "effective_date": "2026-02-01",
        "keywords": ["GPL", "AGPL", "漏洞扫描"],
        "cross_refs": ["PDF-SEC-INFO-2026"],
        "special_rules": [
            "GPL、AGPL、SSPL 等强传染性许可证组件不得直接用于闭源商业交付，确需使用的须经法务复核。",
            "所有新增开源组件上线前必须完成许可证识别、漏洞扫描和维护责任人登记。",
        ],
    },
    {
        "filename": "ai_usage_governance_2026.pdf",
        "doc_id": "PDF-AI-USAGE-2026",
        "title": "生成式AI工具使用与内容审核规范",
        "department": "AI Governance",
        "process_type": "AI工具使用",
        "risk_level": "高",
        "owner": "AI治理委员会",
        "system": "AI工具申请平台",
        "form_id": "AI-F-501",
        "approval_sla": "高风险AI使用场景须在上线前五个工作日完成审核",
        "scope": "员工使用生成式AI工具进行文案、代码、数据分析、客户沟通辅助和知识检索的场景",
        "policy_no": "AI-USAGE-2026-01",
        "version": "V1.5",
        "publish_date": "2026年1月28日",
        "effective_date": "2026-02-01",
        "keywords": ["AI工具", "内容审核", "客户数据"],
        "cross_refs": ["PDF-SEC-DATAEXPORT-2026", "PDF-SEC-INFO-2026"],
        "special_rules": [
            "不得向未经批准的外部AI工具输入客户身份信息、合同价格、源代码、未公开财务数据和内部密级文档。",
            "面向客户或公众发布的AI生成内容必须经过人工复核，并保留提示词、输出结果和复核记录。",
        ],
    },
    {
        "filename": "records_retention_2026.pdf",
        "doc_id": "PDF-LEGAL-RETENTION-2026",
        "title": "业务记录留存与销毁管理规范",
        "department": "Legal",
        "process_type": "记录留存",
        "risk_level": "高",
        "owner": "法务部与内审部",
        "system": "档案管理系统",
        "form_id": "LEG-F-601",
        "approval_sla": "高风险业务记录销毁须提前十个工作日发起审批",
        "scope": "合同、审批记录、客服录音、财务凭证、系统日志、监管报送材料和项目归档资料",
        "policy_no": "LEG-RET-2026-01",
        "version": "V2.6",
        "publish_date": "2026年1月30日",
        "effective_date": "2026-02-01",
        "keywords": ["留存", "销毁", "监管"],
        "cross_refs": ["LEGAL-CONTRACT-2026"],
        "special_rules": [
            "合同、财务凭证和监管报送材料原则上不少于十年留存；客户服务录音不少于三年留存。",
            "涉及争议、诉讼、审计或监管调查的记录不得销毁，即使已超过常规保存期限也应冻结留存。",
        ],
    },
    {
        "filename": "customer_service_quality_2026.pdf",
        "doc_id": "PDF-OPS-CS-QUALITY-2026",
        "title": "客户服务话术质检与升级处理规范",
        "department": "Operations",
        "process_type": "客服质检",
        "risk_level": "中",
        "owner": "客户运营部",
        "system": "客服质检平台",
        "form_id": "OPS-F-701",
        "approval_sla": "重大客诉须在两个小时内完成升级登记",
        "scope": "客服会话质检、话术合规、客户投诉升级、敏感问题复核和服务质量改进",
        "policy_no": "OPS-CS-2026-01",
        "version": "V2.0",
        "publish_date": "2026年2月1日",
        "effective_date": "2026-02-15",
        "keywords": ["客诉", "质检", "升级"],
        "cross_refs": ["PDF-SEC-INFO-2026", "PDF-LEGAL-RETENTION-2026"],
        "special_rules": [
            "涉及客户资金、监管投诉、媒体曝光或人身安全风险的客诉，应在两个小时内升级至二线负责人。",
            "客服人员不得承诺制度外赔付、退款或补偿方案，确需例外处理的应由运营负责人审批。",
        ],
    },
    {
        "filename": "procurement_policy_2026.pdf",
        "doc_id": "PDF-PROC-PURCHASE-2026",
        "title": "采购申请与供应商准入管理制度",
        "department": "Procurement",
        "process_type": "采购申请",
        "risk_level": "中",
        "owner": "采购部与财务部",
        "system": "采购管理平台",
        "form_id": "PROC-F-801",
        "approval_sla": "单笔金额超过十万元的采购应提前五个工作日发起评审",
        "scope": "办公采购、软件服务、咨询服务、外包服务、硬件设备和供应商准入",
        "policy_no": "PROC-PUR-2026-01",
        "version": "V2.1",
        "publish_date": "2026年2月3日",
        "effective_date": "2026-02-15",
        "keywords": ["供应商", "采购", "招投标"],
        "cross_refs": ["FIN-BUDGET-2026", "PDF-FIN-EXP-2026"],
        "special_rules": [
            "同一供应商年度累计采购金额超过三十万元的，应完成供应商复审和廉洁合规确认。",
            "紧急采购可先行执行风险评估，但应在三个工作日内补齐预算、合同和验收材料。",
        ],
    },
    {
        "filename": "data_export_policy_2026.pdf",
        "doc_id": "PDF-SEC-DATAEXPORT-2026",
        "title": "客户数据导出与外发审批制度",
        "department": "Security",
        "process_type": "数据导出",
        "risk_level": "高",
        "owner": "信息安全部与法务部",
        "system": "数据安全审批平台",
        "form_id": "SEC-F-302",
        "approval_sla": "含客户身份信息的数据导出须至少提前三个工作日提交",
        "scope": "客户数据、业务明细、日志数据、分析报表和需要外发的数据文件",
        "policy_no": "SEC-DATA-2026-01",
        "version": "V2.7",
        "publish_date": "2026年2月5日",
        "effective_date": "2026-02-15",
        "keywords": ["客户数据", "外发", "脱敏"],
        "cross_refs": ["PDF-SEC-INFO-2026", "PDF-AI-USAGE-2026"],
        "special_rules": [
            "导出客户身份信息、联系方式、交易记录或行为日志前，应完成脱敏评估和接收方确认。",
            "未经审批不得通过个人邮箱、网盘、即时通讯工具或移动存储设备外发客户数据。",
        ],
    },
    {
        "filename": "business_continuity_2026.pdf",
        "doc_id": "PDF-OPS-BCP-2026",
        "title": "业务连续性演练与应急响应制度",
        "department": "Operations",
        "process_type": "业务连续性",
        "risk_level": "高",
        "owner": "运营管理部与信息技术部",
        "system": "应急响应平台",
        "form_id": "OPS-F-702",
        "approval_sla": "年度业务连续性演练计划应在每年第一季度完成审批",
        "scope": "关键业务系统、客户服务、支付结算、数据同步和跨部门应急协作",
        "policy_no": "OPS-BCP-2026-01",
        "version": "V1.9",
        "publish_date": "2026年2月8日",
        "effective_date": "2026-02-15",
        "keywords": ["演练", "应急", "恢复"],
        "cross_refs": ["IT-INCIDENT-2026", "PDF-SEC-INFO-2026"],
        "special_rules": [
            "核心业务系统应至少每半年组织一次恢复演练，演练结果应形成整改清单。",
            "发生影响客户服务连续性的重大事件时，应在三十分钟内启动应急响应并同步客服口径。",
        ],
    },
]


def cn_date_to_iso(value: str) -> str:
    return value.replace("年", "-").replace("月", "-").replace("日", "")


def clean_output_dir() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for path in PDF_DIR.glob("*.pdf"):
        path.unlink()
    for path in PDF_DIR.glob("*.metadata.json"):
        path.unlink()


def header_footer(canvas, doc, spec: dict) -> None:
    canvas.saveState()
    canvas.setFont("STSong-Light", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(18 * mm, 287 * mm, COMPANY_NAME)
    canvas.drawRightString(192 * mm, 287 * mm, f"{spec['policy_no']} | {spec['version']} | 内部资料")
    canvas.line(18 * mm, 284 * mm, 192 * mm, 284 * mm)
    canvas.drawString(18 * mm, 11 * mm, f"制度名称：{spec['title']}")
    canvas.drawRightString(192 * mm, 11 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def make_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName="STSong-Light", fontSize=22, leading=30, alignment=TA_CENTER, spaceAfter=18),
        "cover_subtitle": ParagraphStyle("cover_subtitle", parent=base["Normal"], fontName="STSong-Light", fontSize=11, leading=18, alignment=TA_CENTER, spaceAfter=5),
        "chapter": ParagraphStyle("chapter", parent=base["Heading1"], fontName="STSong-Light", fontSize=15, leading=22, spaceBefore=12, spaceAfter=8),
        "article": ParagraphStyle("article", parent=base["Heading2"], fontName="STSong-Light", fontSize=11.5, leading=18, spaceBefore=7, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="STSong-Light", fontSize=10, leading=16, firstLineIndent=20, alignment=TA_LEFT),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="STSong-Light", fontSize=8.5, leading=13),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontName="STSong-Light", fontSize=8.5, leading=12),
    }


def table(data: list[list[str]], widths: list[int], styles: dict) -> Table:
    content = [[Paragraph(str(cell), styles["table"]) for cell in row] for row in data]
    t = Table(content, colWidths=[width * mm for width in widths], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def paragraph(text: str, style_name: str, styles: dict) -> Paragraph:
    return Paragraph(text, styles[style_name])


def build_formal_story(spec: dict, styles: dict) -> list:
    story = [
        Spacer(1, 32 * mm),
        paragraph(f"{COMPANY_NAME}{spec['title']}", "cover_title", styles),
        paragraph(f"制度编号：{spec['policy_no']}", "cover_subtitle", styles),
        paragraph(f"版本号：{spec['version']}", "cover_subtitle", styles),
        paragraph(f"发布日期：{spec['publish_date']}", "cover_subtitle", styles),
        paragraph(f"生效日期：{spec['effective_date']}", "cover_subtitle", styles),
        paragraph(f"适用范围：{spec['scope']}", "cover_subtitle", styles),
        Spacer(1, 12 * mm),
        table(
            [
                ["字段", "内容"],
                ["制度密级", "内部资料"],
                ["归口部门", spec["department"]],
                ["解释权归属", spec["owner"]],
                ["办理系统", spec["system"]],
                ["适用流程", spec["process_type"]],
            ],
            [35, 125],
            styles,
        ),
        PageBreak(),
        paragraph("修订记录", "chapter", styles),
        table(
            [
                ["版本", "发布日期", "修订内容", "审批人"],
                ["V1.0", "2025年6月1日", "首次发布制度框架和基础办理要求。", spec["owner"]],
                [spec["version"], spec["publish_date"], "补充例外条件、跨制度引用、审批流程和附件要求。", spec["owner"]],
            ],
            [22, 34, 80, 34],
            styles,
        ),
        Spacer(1, 8),
        paragraph("审批流程", "chapter", styles),
        table(
            [
                ["环节", "责任角色", "处理要求", "时限"],
                ["申请提交", "申请人", f"在{spec['system']}填写事项说明并上传{spec['form_id']}。", "T日"],
                ["主管审批", "直属主管", "确认业务必要性、影响范围和资源占用。", "1个工作日"],
                ["专业复核", spec["owner"], "复核制度适用性、风险等级、材料完整性和例外条件。", spec["approval_sla"]],
                ["归档确认", "执行部门", "回填结果并保留审批记录、执行证据和附件材料。", "3个工作日"],
            ],
            [24, 34, 84, 28],
            styles,
        ),
        PageBreak(),
        paragraph("第一章 总则", "chapter", styles),
    ]

    for item in BASE_ARTICLES[:3]:
        story.append(paragraph(item.format(**spec), "body", styles))
        story.append(Spacer(1, 4))

    story.extend(
        [
            paragraph("第二章 适用范围与职责", "chapter", styles),
            paragraph(BASE_ARTICLES[3].format(**spec), "body", styles),
            paragraph(BASE_ARTICLES[4].format(**spec), "body", styles),
            paragraph("第十一条 归口部门应定期复盘制度执行情况，对高频咨询、审批退回、例外流程和风险事件进行分析，并推动制度修订。", "body", styles),
            paragraph("第十二条 员工、主管和执行部门应按照岗位职责配合制度落地，不得将审批责任转移给无授权人员。", "body", styles),
            paragraph("第三章 办理要求", "chapter", styles),
            paragraph(BASE_ARTICLES[5].format(**spec), "body", styles),
            paragraph(f"第十三条 申请材料至少包括{spec['form_id']}、事项说明、影响范围、联系人、期望完成时间和必要证明材料。", "body", styles),
            paragraph("第十四条 材料不齐或信息不一致的，审批人可以退回补充；申请人应在两个工作日内补齐，逾期未处理的，系统可关闭流程。", "body", styles),
            paragraph("第十五条 申请事项发生变化的，应撤回原流程后重新提交，不得通过线下沟通绕过系统审批。", "body", styles),
            paragraph("第四章 风险控制与例外条件", "chapter", styles),
            paragraph(BASE_ARTICLES[6].format(**spec), "body", styles),
            paragraph(BASE_ARTICLES[7].format(**spec), "body", styles),
        ]
    )

    for offset, rule in enumerate(spec["special_rules"], 16):
        story.append(paragraph(f"第{offset}条 {rule}", "body", styles))

    refs = "、".join(f"《{ref}》" for ref in spec["cross_refs"])
    story.extend(
        [
            paragraph("第五章 交叉引用与版本适用", "chapter", styles),
            paragraph(f"第二十条 本制度与{refs}存在业务关联。处理跨制度事项时，应先确认事项主责部门，再按风险等级补充相关审批。", "body", styles),
            paragraph(f"第二十一条 本制度当前版本为{spec['version']}，自{spec['effective_date']}起生效。旧版制度与本制度不一致的，以本制度为准。", "body", styles),
            paragraph("第二十二条 若专项制度与本制度存在冲突，应由制度归口部门会同法务或内审确认适用顺序，并形成书面记录。", "body", styles),
            paragraph("第六章 归档、监督与责任", "chapter", styles),
            paragraph(BASE_ARTICLES[8].format(**spec), "body", styles),
            paragraph("第二十三条 审批流水、附件、执行记录和复核意见应至少保存三年；涉及合同、财务、客户数据或监管事项的，按专项制度延长保存期限。", "body", styles),
            paragraph("第二十四条 内审或合规部门可对制度执行情况进行抽查，发现问题的，相关部门应在整改期限内提交整改结果。", "body", styles),
            paragraph("第二十五条 违反本制度造成损失或风险事件的，按照员工手册、信息安全制度和相关专项制度追究责任。", "body", styles),
            paragraph("第七章 附则", "chapter", styles),
            paragraph(BASE_ARTICLES[9].format(**spec), "body", styles),
            paragraph("第二十六条 本制度未尽事项，由制度归口部门结合业务实际和公司管理要求另行发布操作指引。", "body", styles),
            PageBreak(),
            paragraph("附件一 材料清单", "chapter", styles),
            table(
                [
                    ["材料名称", "提交人", "是否必填", "说明"],
                    [spec["form_id"], "申请人", "是", "包含申请原因、影响范围、联系人和期望完成时间。"],
                    ["主管审批意见", "直属主管", "是", "确认业务必要性和执行风险。"],
                    ["风险评估或补充说明", "申请人", "视情况", "高风险、例外流程或跨部门事项必须提交。"],
                    ["执行结果记录", "执行部门", "是", "流程办结后回填，作为后续审计依据。"],
                ],
                [42, 28, 24, 76],
                styles,
            ),
            Spacer(1, 10),
            paragraph("附件二 审批流程图说明", "chapter", styles),
            paragraph(f"申请人提交{spec['form_id']}后，系统自动流转至直属主管；涉及高风险事项时，追加{spec['owner']}复核；复核通过后由执行部门办理并归档。", "body", styles),
            paragraph("解释权归属", "chapter", styles),
            paragraph(f"本制度由{spec['owner']}负责解释。跨部门争议由流程负责人组织业务、法务、信息安全、财务或内审共同确认。", "body", styles),
        ]
    )

    return story


def metadata_for(spec: dict) -> dict:
    payload = {
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
    return payload


def eval_cases_for(spec: dict) -> Iterable[dict]:
    slug = spec["doc_id"].lower().replace("pdf-", "").replace("-", "_")
    base = {
        "expected_doc_ids": [spec["doc_id"]],
        "department": spec["department"],
        "should_refuse": False,
    }
    cases = [
        {
            "id": f"{slug}_scope",
            "question": f"{spec['title']}适用于哪些人员或场景？",
            "expected_sections": ["第一章 总则"],
            "reference_answer": f"适用范围包括{spec['scope']}。",
            "question_type": "PDF-事实型",
        },
        {
            "id": f"{slug}_sla",
            "question": f"{spec['title']}的审批或办理时限是什么？",
            "expected_sections": ["第三章 办理要求"],
            "reference_answer": f"标准办理时限为：{spec['approval_sla']}。",
            "question_type": "PDF-时限型",
        },
        {
            "id": f"{slug}_materials",
            "question": f"办理{spec['process_type']}需要提交哪些材料？",
            "expected_sections": ["附件一 材料清单"],
            "reference_answer": f"至少需要提交{spec['form_id']}、主管审批意见、必要证明材料和执行结果记录。",
            "question_type": "PDF-材料型",
        },
        {
            "id": f"{slug}_exception",
            "question": f"{spec['process_type']}遇到紧急或例外情况怎么处理？",
            "expected_sections": ["第四章 风险控制与例外条件"],
            "reference_answer": "紧急事项可以启动例外流程，但必须说明紧急原因、临时控制措施、影响范围和事后补审计划。",
            "question_type": "PDF-例外条件型",
        },
        {
            "id": f"{slug}_cross_ref",
            "question": f"{spec['title']}和哪些制度存在交叉引用？",
            "expected_sections": ["第五章 交叉引用与版本适用"],
            "reference_answer": f"相关制度包括：{','.join(spec['cross_refs'])}。",
            "question_type": "PDF-跨文档引用型",
        },
        {
            "id": f"{slug}_version",
            "question": f"{spec['title']}当前版本和生效日期是什么？",
            "expected_sections": ["第五章 交叉引用与版本适用"],
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


def main() -> None:
    clean_output_dir()
    styles = make_styles()
    for spec in PDF_SPECS:
        generate_pdf(spec, styles)

    PDF_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PDF_EVAL_PATH.open("w", encoding="utf-8") as handle:
        for spec in PDF_SPECS:
            for case in eval_cases_for(spec):
                handle.write(json.dumps(case, ensure_ascii=False) + "\n")
        refusal_cases = [
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
        ]
        for case in refusal_cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"generated_pdf_policies={len(PDF_SPECS)}")
    print(f"generated_pdf_eval_cases={len(PDF_SPECS) * 6 + 2}")


if __name__ == "__main__":
    main()
