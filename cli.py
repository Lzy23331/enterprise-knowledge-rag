import sys

from smart_office_rag.pipeline import EnterpriseKnowledgeRAG


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "新员工如何申请邮箱和 VPN 权限？"
    rag = EnterpriseKnowledgeRAG()
    rag.initialize()
    response = rag.ask(question)
    print(response.answer)
    print("\n--- 引用来源 ---")
    for source in response.sources:
        print(f"- {source['citation']} ({source['department']} / {source['risk_level']})")


if __name__ == "__main__":
    main()
