import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = PROJECT_ROOT / "data" / "policies"
EVAL_DIR = PROJECT_ROOT / "data" / "eval"


DOC_SPECS = [
    ("HR-LEAVE-2026", "员工请假与休假管理制度", "HR", "请假申请", "低", "人力资源部", "员工服务系统", "HR-F-001", "年假至少提前三个工作日，连续超过五个工作日提前七个工作日", "年假、病假、婚假、产假、陪产假等假期申请"),
    ("HR-ONBOARD-2026", "员工入职与离职办理流程", "HR", "入离职流程", "中", "人力资源部", "员工服务系统", "HR-F-002", "入职前两个工作日完成账号预开通，离职当天关闭权限", "入职材料、工牌、账号、离职交接和权限关闭"),
    ("HR-TRAIN-2026", "员工培训与考试管理办法", "HR", "培训考试", "低", "学习发展中心", "学习平台", "HR-F-003", "新员工入职三十日内完成必修课", "必修培训、岗位认证、考试补考和培训记录归档"),
    ("HR-PERF-2026", "绩效目标与考核申诉流程", "HR", "绩效管理", "中", "人力资源部", "绩效系统", "HR-F-004", "绩效申诉须在结果发布后三个工作日内提交", "绩效目标设定、季度复盘、结果确认和申诉处理"),
    ("HR-TRANSFER-2026", "员工内部转岗与借调流程", "HR", "岗位变更", "中", "人力资源部", "员工服务系统", "HR-F-005", "转岗申请至少提前十个工作日发起", "内部转岗、临时借调、组织调整和权限变更"),
    ("FIN-EXP-2026", "差旅与费用报销管理规范", "Finance", "报销申请", "中", "财务部", "报销系统", "FIN-F-001", "差旅结束后十五个自然日内提交报销", "差旅费、交通费、住宿费、招待费和补贴报销"),
    ("FIN-ADV-2026", "备用金与借款申请规范", "Finance", "借款申请", "中", "财务部", "财务共享平台", "FIN-F-002", "备用金借款应在事项结束后十个工作日内核销", "项目备用金、临时借款、核销和逾期处理"),
    ("FIN-INVOICE-2026", "发票开具与收票验真流程", "Finance", "发票管理", "中", "税务管理组", "发票管理平台", "FIN-F-003", "收票后三个工作日内完成验真", "发票开具、收票验真、红冲和税号信息维护"),
    ("FIN-BUDGET-2026", "部门预算申请与调整流程", "Finance", "预算管理", "中", "财务计划组", "预算系统", "FIN-F-004", "预算调整须在费用发生前完成审批", "年度预算、月度滚动预测、预算冻结和预算调整"),
    ("FIN-PAYMENT-2026", "供应商付款与对账流程", "Finance", "付款申请", "高", "财务共享中心", "付款系统", "FIN-F-005", "付款申请至少提前五个工作日提交", "供应商付款、合同匹配、三单校验和银行信息复核"),
    ("IT-PERM-2026", "IT 系统权限申请与审批规范", "IT", "权限申请", "高", "信息技术部", "IT 服务台", "IT-F-001", "高风险权限默认最长有效期三个月", "邮箱、VPN、代码仓库、数据平台、生产系统和业务系统权限"),
    ("IT-VPN-2026", "VPN 与办公账号服务指南", "IT", "IT 服务", "中", "IT 服务台", "IT 服务台", "IT-F-002", "普通账号问题一个工作日内响应，VPN 开通两个工作日内完成", "企业邮箱、VPN、账号解锁、动态口令和终端登录问题"),
    ("IT-ASSET-2026", "办公电脑与移动设备领用规范", "IT", "资产领用", "中", "终端支持组", "资产管理系统", "IT-F-003", "设备领用应在入职或项目开始前两个工作日提交", "电脑、显示器、手机、加密 U 盘和设备归还"),
    ("IT-INCIDENT-2026", "IT 故障工单与服务级别规范", "IT", "故障处理", "中", "IT 服务台", "ITSM 系统", "IT-F-004", "一级故障十五分钟响应，普通故障一个工作日响应", "办公网络、系统登录、打印、会议设备和业务系统故障"),
    ("IT-CHANGE-2026", "生产系统变更与应急处理规范", "IT", "变更申请", "高", "变更管理委员会", "变更管理平台", "IT-F-005", "普通生产变更至少提前三个工作日提交", "生产发布、配置变更、数据库脚本、回滚和应急变更"),
    ("SEC-DATA-2026", "数据安全与客户信息保护规范", "Security", "数据合规", "高", "信息安全部", "数据权限平台", "SEC-F-001", "高敏感数据导出须在审批通过后二十四小时内完成", "客户数据、员工数据、交易数据、合同数据和系统日志保护"),
    ("SEC-ACCESS-2026", "访客入场与办公区域安全规范", "Security", "现场安全", "中", "行政与安全部", "访客系统", "SEC-F-002", "外部访客至少提前一个工作日预约", "访客预约、门禁、陪同、拍照限制和临时工牌归还"),
    ("SEC-PHISHING-2026", "钓鱼邮件与安全事件上报流程", "Security", "安全事件", "高", "安全运营中心", "安全事件平台", "SEC-F-003", "疑似钓鱼邮件应在发现后三十分钟内上报", "钓鱼邮件、异常登录、恶意附件和账号泄露上报"),
    ("SEC-CLASSIFY-2026", "信息分级分类与资料外发规范", "Security", "数据分级", "高", "信息安全部", "数据分级平台", "SEC-F-004", "秘密级资料外发须经部门负责人和信息安全审批", "公开、内部、敏感、秘密资料分级和外发控制"),
    ("SEC-AUDIT-2026", "日志审计与账号复核管理办法", "Security", "审计复核", "高", "安全运营中心", "审计平台", "SEC-F-005", "高风险系统账号至少每月复核一次", "日志留存、账号复核、异常告警和审计取证"),
    ("ADM-MEETING-2026", "会议室与访客接待管理规范", "Admin", "行政服务", "低", "行政部", "行政服务平台", "ADM-F-001", "大型会议室需提前两个工作日预订", "会议室预订、访客接待、茶歇、设备和会后整理"),
    ("ADM-SEAL-2026", "印章使用与文件盖章流程", "Admin", "印章申请", "高", "行政法务联合组", "印章系统", "ADM-F-002", "合同类盖章须完成法务和财务审核后提交", "公章、合同章、法人章、授权书和盖章记录"),
    ("ADM-TRAVEL-2026", "出差预订与行政支持流程", "Admin", "出差支持", "低", "行政部", "差旅平台", "ADM-F-003", "机票酒店预订应在出差前两个工作日完成", "机票、酒店、用车、签证支持和行程变更"),
    ("LEGAL-CONTRACT-2026", "合同评审与归档管理办法", "Legal", "合同评审", "高", "法务部", "合同管理系统", "LEG-F-001", "标准合同三个工作日内完成评审，非标合同五个工作日内完成", "销售合同、采购合同、保密协议、补充协议和合同归档"),
    ("LEGAL-NDA-2026", "保密协议与对外信息披露规范", "Legal", "保密合规", "高", "法务部", "合同管理系统", "LEG-F-002", "对外披露敏感信息前必须完成 NDA 或等效保密安排", "NDA、商业秘密、客户名单、技术资料和媒体披露"),
    ("PROC-VENDOR-2026", "供应商准入与年度复评流程", "Procurement", "供应商管理", "中", "采购部", "供应商门户", "PROC-F-001", "新供应商准入评审通常五个工作日内完成", "供应商资质、黑名单筛查、年度复评和退出"),
    ("PROC-BIDDING-2026", "采购寻源与招投标管理办法", "Procurement", "采购申请", "高", "采购部", "采购系统", "PROC-F-002", "预计金额超过十万元应至少三方比价或招标", "采购申请、询价、比价、招标、定标和采购归档"),
    ("AUDIT-ISSUE-2026", "内审问题整改与跟踪流程", "Audit", "审计整改", "高", "内审部", "审计整改平台", "AUD-F-001", "一般问题三十日内完成整改，高风险问题十五日内提交整改计划", "审计发现、整改计划、证据上传、延期申请和关闭验证"),
    ("AUDIT-EVIDENCE-2026", "监管检查资料准备与报送规范", "Audit", "监管报送", "高", "内审与合规部", "监管报送平台", "AUD-F-002", "监管资料报送前必须完成双人复核", "监管检查、资料清单、证明材料、脱敏和报送留痕"),
    ("OPS-BCP-2026", "业务连续性演练与应急预案规范", "Operations", "应急演练", "高", "运营管理部", "应急管理平台", "OPS-F-001", "关键业务系统每年至少完成一次应急演练", "业务连续性计划、应急演练、恢复目标和复盘整改"),
]


def build_policy(spec: tuple[str, ...]) -> str:
    doc_id, title, department, process_type, risk_level, owner, system, form, sla, scope = spec
    return f"""---
doc_id: {doc_id}
title: {title}
department: {department}
process_type: {process_type}
risk_level: {risk_level}
doc_type: 制度
version: v2026.1
effective_date: 2026-01-01
deprecated_date: ""
updated_at: 2026-05-30
owner: {owner}
system: {system}
form_id: {form}
approval_sla: {sla}
---

# {title}

## 适用对象

本制度适用于公司正式员工、试用期员工、外包人员以及因业务需要参与相关流程的合作方。制度覆盖范围包括：{scope}。涉及跨部门协作时，申请人、直属主管、流程负责人和审批部门均应按照本制度留存操作记录。

## 办理条件

申请人应具备真实业务背景，申请事项应与岗位职责、项目任务或合规要求直接相关。涉及中高风险事项时，应补充业务原因、使用期限、影响范围、数据范围、费用预算或回滚安排。禁止使用他人账号代提申请，禁止绕过系统线下审批。

## 办理步骤

1. 申请人在{system}选择“{process_type}”流程，并填写事项说明、所属部门、期望完成时间和联系人。
2. 上传表单编号 {form} 对应材料，必要时补充截图、合同、预算、审批邮件或风险评估记录。
3. 直属主管确认业务必要性，流程负责人核验制度适用范围和材料完整性。
4. {owner} 按照审批 SLA 进行审核，必要时发起财务、法务、信息安全或内审会签。
5. 审批通过后，系统生成流水号并通知申请人；执行部门完成处理后更新处理结果。
6. 申请人确认结果并在系统中关闭流程，相关记录至少保存三年，监管或审计要求更高时按更高要求执行。

## 所需材料

- {form} 申请单，包含申请原因、影响范围、期望完成时间和联系人。
- 直属主管审批意见；高风险事项需补充部门负责人审批。
- 与事项相关的证明材料，例如合同、预算、截图、人员清单、数据字段清单、回滚计划或验收记录。
- 涉及客户数据、生产系统、付款、印章或合同的事项，应补充合规审查或风险评估记录。

## 审批 SLA 与例外流程

标准时限：{sla}。若材料缺失，审批时限从申请人补齐材料后重新计算。紧急事项可走例外流程，但申请人必须说明紧急原因、临时控制措施和事后补审时间。例外流程不得用于规避常规审批，连续两次使用例外流程的部门需接受流程复盘。

## 注意事项

风险等级为“{risk_level}”。申请人应确保填写内容真实、完整、可追溯。涉及高风险权限、客户信息、资金支付、合同承诺、印章使用或监管报送时，必须保留审批记录和执行证据。未经审批不得提前执行，不得将审批截图替代系统流水。

## 常见问题

### 申请被退回怎么办

申请人应根据退回原因补充材料，并在两个工作日内重新提交。超过两个工作日未处理的，系统可自动关闭流程。

### 审批完成后发现信息填错怎么办

申请人不得直接修改已生效结果，应在{system}发起变更或撤销流程，并说明原流水号、错误信息和修正原因。

### 谁负责最终解释

本制度由{owner}负责解释。跨部门争议由流程负责人组织业务、财务、法务、信息安全或内审共同确认。
"""


def build_eval_cases() -> list[dict]:
    cases: list[dict] = []
    for spec in DOC_SPECS:
        doc_id, title, department, process_type, risk_level, owner, system, form, sla, scope = spec
        base_id = doc_id.lower().replace("-", "_")
        cases.extend(
            [
                {
                    "id": f"{base_id}_process",
                    "question": f"{title}的办理步骤是什么？",
                    "expected_doc_ids": [doc_id],
                    "expected_sections": ["办理步骤"],
                    "reference_answer": f"应在{system}发起{process_type}流程，填写事项说明并上传 {form}，经主管和{owner}审核后执行并归档。",
                    "question_type": "流程类",
                    "department": department,
                    "should_refuse": False,
                },
                {
                    "id": f"{base_id}_materials",
                    "question": f"办理{process_type}需要哪些材料？",
                    "expected_doc_ids": [doc_id],
                    "expected_sections": ["所需材料"],
                    "reference_answer": f"需要提交 {form} 申请单、主管审批意见和相关证明材料，高风险事项还需风险评估或会签记录。",
                    "question_type": "材料类",
                    "department": department,
                    "should_refuse": False,
                },
                {
                    "id": f"{base_id}_sla",
                    "question": f"{process_type}的审批时限或提前要求是什么？",
                    "expected_doc_ids": [doc_id],
                    "expected_sections": ["审批 SLA 与例外流程"],
                    "reference_answer": f"标准时限或提前要求为：{sla}；材料缺失时从补齐后重新计算。",
                    "question_type": "时限类",
                    "department": department,
                    "should_refuse": False,
                },
                {
                    "id": f"{base_id}_risk",
                    "question": f"{title}有哪些风险提示和注意事项？",
                    "expected_doc_ids": [doc_id],
                    "expected_sections": ["注意事项"],
                    "reference_answer": f"该流程风险等级为{risk_level}，必须保留审批记录和执行证据，不得绕过系统审批。",
                    "question_type": "合规类",
                    "department": department,
                    "should_refuse": False,
                },
                {
                    "id": f"{base_id}_system",
                    "question": f"{title}应该在哪个系统提交？",
                    "expected_doc_ids": [doc_id],
                    "expected_sections": ["办理步骤"],
                    "reference_answer": f"应在{system}提交，并选择“{process_type}”流程。",
                    "question_type": "系统入口类",
                    "department": department,
                    "should_refuse": False,
                },
            ]
        )

    refuse_questions = [
        "公司股票什么时候可以买入？",
        "员工子女入学补贴怎么申请？",
        "办公室宠物寄养制度是什么？",
        "私人购房贷款公司能担保吗？",
        "员工个人所得税专项扣除怎么填最省税？",
        "公司是否报销私人健身卡？",
        "如何申请海外永久居留支持？",
        "周末团建不参加会扣绩效吗？",
        "公司是否提供员工购车免息贷款？",
        "如何申请公司宿舍装修报销？",
        "公司内部食堂菜谱在哪里看？",
        "公司是否允许员工投资供应商？",
        "如何申请宠物医疗报销？",
        "员工婚礼礼金标准是多少？",
        "如何查询公司未公开财报？",
        "公司是否给员工办理旅游签证？",
        "办公室咖啡机坏了能否报销咖啡券？",
        "员工停车位摇号规则是什么？",
        "校招内推奖金什么时候发？",
        "公司年会抽奖中奖税费由谁承担？",
        "员工生日礼物在哪里领取？",
        "居家办公能否报销水电费？",
    ]
    for index, question in enumerate(refuse_questions, 1):
        cases.append(
            {
                "id": f"refuse_{index:02d}",
                "question": question,
                "expected_doc_ids": [],
                "expected_sections": [],
                "reference_answer": "当前知识库没有检索到明确依据，应建议联系对应负责部门确认，不得编造制度。",
                "question_type": "知识库外拒答类",
                "department": "Unknown",
                "should_refuse": True,
            }
        )
    return cases


def main() -> None:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    for path in POLICY_DIR.glob("*.md"):
        path.unlink()

    for spec in DOC_SPECS:
        doc_id, title, *_ = spec
        filename = doc_id.lower().replace("-", "_") + ".md"
        (POLICY_DIR / filename).write_text(build_policy(spec), encoding="utf-8")

    cases = build_eval_cases()
    with (EVAL_DIR / "eval_cases.jsonl").open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"generated_policies={len(DOC_SPECS)}")
    print(f"generated_eval_cases={len(cases)}")


if __name__ == "__main__":
    main()
