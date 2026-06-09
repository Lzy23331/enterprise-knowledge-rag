import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "data" / "policies_pdf"


PDF_SPECS = [
    {
        "filename": "ai_usage_governance_2026.pdf",
        "doc_id": "AI-USAGE-2026",
        "title": "生成式 AI 工具使用与内容审核规范",
        "department": "AI Governance",
        "process_type": "AI 工具使用",
        "risk_level": "高",
        "owner": "AI 治理委员会",
        "system": "AI 工具申请平台",
        "form_id": "AI-F-001",
        "approval_sla": "高风险 AI 使用场景须在上线前五个工作日完成审核",
        "scope": "员工使用生成式 AI 工具进行文案、代码、数据分析、客户沟通辅助和知识检索的场景",
    },
    {
        "filename": "remote_work_security_2026.pdf",
        "doc_id": "HR-REMOTE-2026",
        "title": "远程办公与异地协作安全规范",
        "department": "HR",
        "process_type": "远程办公",
        "risk_level": "中",
        "owner": "人力资源部与信息安全部",
        "system": "员工服务系统",
        "form_id": "HR-F-006",
        "approval_sla": "连续远程办公超过三天须至少提前两个工作日提交申请",
        "scope": "居家办公、异地办公、跨城市协作、临时远程接入和外部网络使用",
    },
    {
        "filename": "customer_service_quality_2026.pdf",
        "doc_id": "OPS-CS-QUALITY-2026",
        "title": "客户服务话术质检与升级处理规范",
        "department": "Operations",
        "process_type": "客服质检",
        "risk_level": "中",
        "owner": "客户运营部",
        "system": "客服质检平台",
        "form_id": "OPS-F-002",
        "approval_sla": "重大客诉须在两个小时内完成升级登记",
        "scope": "客服会话质检、话术合规、客户投诉升级、敏感问题复核和服务质量改进",
    },
    {
        "filename": "records_retention_2026.pdf",
        "doc_id": "LEGAL-RETENTION-2026",
        "title": "业务记录留存与销毁管理规范",
        "department": "Legal",
        "process_type": "记录留存",
        "risk_level": "高",
        "owner": "法务部与内审部",
        "system": "档案管理系统",
        "form_id": "LEG-F-003",
        "approval_sla": "高风险业务记录销毁须提前十个工作日发起审批",
        "scope": "合同、审批记录、客服录音、财务凭证、系统日志、监管报送材料和项目归档资料",
    },
    {
        "filename": "open_source_compliance_2026.pdf",
        "doc_id": "IT-OSS-2026",
        "title": "开源软件引入与许可证合规规范",
        "department": "IT",
        "process_type": "开源合规",
        "risk_level": "高",
        "owner": "技术委员会与法务部",
        "system": "研发资产管理平台",
        "form_id": "IT-F-006",
        "approval_sla": "引入 GPL/AGPL 类许可证组件须在上线前五个工作日完成法务复核",
        "scope": "开源组件选型、许可证审查、漏洞扫描、版本升级、二次分发和开源义务履行",
    },
]


def build_policy_text(spec: dict) -> list[tuple[str, str]]:
    front_matter = "\n".join(
        [
            "---",
            f"doc_id: {spec['doc_id']}",
            f"title: {spec['title']}",
            f"department: {spec['department']}",
            f"process_type: {spec['process_type']}",
            f"risk_level: {spec['risk_level']}",
            "doc_type: PDF制度",
            "version: v2026.1",
            "effective_date: 2026-02-01",
            "updated_at: 2026-06-01",
            f"owner: {spec['owner']}",
            f"system: {spec['system']}",
            f"form_id: {spec['form_id']}",
            f"approval_sla: {spec['approval_sla']}",
            "---",
        ]
    )
    return [
        ("Code", front_matter),
        ("Title", f"# {spec['title']}"),
        ("Heading2", "## 适用范围"),
        ("Body", f"本规范适用于{spec['scope']}。涉及跨部门协作、外部系统、客户信息或监管要求时，申请人应保留完整审批和执行记录。"),
        ("Heading2", "## 准入条件"),
        ("Body", f"申请人应说明真实业务背景、使用目的、影响范围、涉及系统和预期完成时间。涉及高风险事项时，应补充风险评估、回滚安排、合规审查或负责人确认记录。"),
        ("Heading2", "## 办理步骤"),
        ("Body", f"1. 申请人在{spec['system']}选择“{spec['process_type']}”流程并填写事项说明。"),
        ("Body", f"2. 上传 {spec['form_id']} 申请单以及必要证明材料。"),
        ("Body", f"3. 直属主管确认业务必要性，{spec['owner']}进行制度适用性和风险审查。"),
        ("Body", "4. 审批通过后，执行部门完成处理并在系统中回填处理结果。"),
        ("Body", "5. 申请人确认结果，相关记录按照制度要求归档保存。"),
        ("Heading2", "## 所需材料"),
        ("Body", f"- {spec['form_id']} 申请单，包含申请原因、影响范围、联系人和期望完成时间。"),
        ("Body", "- 直属主管审批意见；高风险事项需补充部门负责人或合规负责人审批。"),
        ("Body", "- 与事项相关的截图、清单、合同、评估报告、系统记录或复核结论。"),
        ("Heading2", "## 审批 SLA 与例外流程"),
        ("Body", f"标准时限：{spec['approval_sla']}。材料缺失时，从补齐材料后重新计算审批时限。紧急事项可走例外流程，但必须说明紧急原因、临时控制措施和事后补审计划。"),
        ("Heading2", "## 注意事项"),
        ("Body", f"风险等级为“{spec['risk_level']}”。未经审批不得提前执行，不得用即时通讯截图替代系统审批流水。涉及客户、监管、资金、代码、算法或外部披露事项时，必须保留审查证据。"),
        ("Heading2", "## 常见问题"),
        ("Heading3", "### 材料不齐被退回怎么办"),
        ("Body", "申请人应按照退回原因补充材料，并在两个工作日内重新提交；超过时限未处理的，系统可关闭流程。"),
        ("Heading3", "### 谁负责最终解释"),
        ("Body", f"本规范由{spec['owner']}负责解释。跨部门争议由流程负责人组织业务、法务、信息安全、财务或内审共同确认。"),
    ]


def generate_pdf(spec: dict) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CnTitle", parent=styles["Title"], fontName="STSong-Light", fontSize=18, leading=24))
    styles.add(ParagraphStyle(name="CnHeading2", parent=styles["Heading2"], fontName="STSong-Light", fontSize=14, leading=20))
    styles.add(ParagraphStyle(name="CnHeading3", parent=styles["Heading3"], fontName="STSong-Light", fontSize=12, leading=18))
    styles.add(ParagraphStyle(name="CnBody", parent=styles["BodyText"], fontName="STSong-Light", fontSize=10.5, leading=16))
    styles.add(ParagraphStyle(name="CnCode", parent=styles["Code"], fontName="STSong-Light", fontSize=7.5, leading=9))

    story = []
    for kind, text in build_policy_text(spec):
        style = {
            "Title": styles["CnTitle"],
            "Heading2": styles["CnHeading2"],
            "Heading3": styles["CnHeading3"],
            "Code": styles["CnCode"],
        }.get(kind, styles["CnBody"])
        story.append(Paragraph(text.replace("\n", "<br/>"), style))
        story.append(Spacer(1, 8))

    doc = SimpleDocTemplate(str(PDF_DIR / spec["filename"]), pagesize=A4)
    doc.build(story)

    metadata = {
        key: spec[key]
        for key in [
            "doc_id",
            "title",
            "department",
            "process_type",
            "risk_level",
            "owner",
            "system",
            "form_id",
            "approval_sla",
        ]
    }
    metadata.update(
        {
            "doc_type": "PDF制度",
            "version": "v2026.1",
            "effective_date": "2026-02-01",
            "updated_at": "2026-06-01",
        }
    )
    sidecar_path = PDF_DIR / spec["filename"]
    sidecar_path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    for spec in PDF_SPECS:
        generate_pdf(spec)
    print(f"generated_pdf_policies={len(PDF_SPECS)}")


if __name__ == "__main__":
    main()
