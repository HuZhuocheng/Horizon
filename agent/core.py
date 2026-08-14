import json
import time
import os
from openai import OpenAI

class CreditRiskAgent:
    def __init__(self, rules_path="mock_data/rules.json", api_key=None, base_url=None, model="qwen-plus"):
        self.rules_path = rules_path
        self.rules = self._load_rules()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                self.client = None
        else:
            self.client = None

    def update_llm_config(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None
            
    def _load_rules(self):
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", [])
        except Exception as e:
            return []
            
    def parse_documents(self, files):
        """
        子任务 1：多模态文档解析
        """
        time.sleep(1.5) # 模拟解析耗时
        return {
            "company_name": "XX 制造有限公司（模拟）",
            "financials": {
                "asset_liability_ratio": 75.2, # 资产负债率 %
                "current_ratio": 1.2,          # 流动比率
            },
            "legal": [
                {"case_type": "被执行人", "amount_w_rmb": 150, "status": "未结案"}
            ],
            "business": {
                "recent_equity_change": True,
                "months_since_change": 3
            }
        }
        
    def run_rule_engine(self, extracted_data):
        """
        子任务 2 & 3：调用风控规则知识库进行校验
        """
        time.sleep(1.0) # 模拟规则匹配耗时
        results = []
        
        # 1. 资产负债率校验 (R001)
        al_ratio = extracted_data["financials"]["asset_liability_ratio"]
        if al_ratio > 70:
            results.append({
                "rule_id": "R001",
                "risk_level": "high",
                "detail": f"提取到资产负债率为 {al_ratio}%，超过 70% 的行业预警阈值。",
                "suggestion": "资产负债率过高，存在较大偿债风险，建议进一步核实负债结构。"
            })
            
        # 2. 流动比率校验 (R003)
        c_ratio = extracted_data["financials"]["current_ratio"]
        if c_ratio < 1.5:
            results.append({
                "rule_id": "R003",
                "risk_level": "medium",
                "detail": f"提取到流动比率为 {c_ratio}，低于 1.5。",
                "suggestion": "流动比率偏低，短期偿债能力可能不足。"
            })
            
        # 3. 涉诉校验 (R002)
        for case in extracted_data["legal"]:
            if case["case_type"] == "被执行人" or case["amount_w_rmb"] > 100:
                results.append({
                    "rule_id": "R002",
                    "risk_level": "high",
                    "detail": f"发现未结案的被执行案件，涉案金额约 {case['amount_w_rmb']} 万元。",
                    "suggestion": "存在重大未结诉讼或被执行记录，存在资金冻结风险。"
                })
                
        # 4. 股权变更校验 (R004)
        if extracted_data["business"]["recent_equity_change"] and extracted_data["business"]["months_since_change"] < 6:
            results.append({
                "rule_id": "R004",
                "risk_level": "medium",
                "detail": f"近 {extracted_data['business']['months_since_change']} 个月内发生过股权变更。",
                "suggestion": "近期存在股权变更，需关注企业实际控制权稳定性。"
            })
            
        return results

    def generate_report(self, extracted_data, risk_results):
        """
        子任务 4：风险标记与报告生成
        """
        time.sleep(0.5)
        
        report = f"## Horizon 尽调简报：{extracted_data['company_name']}\n\n"
        report += "### 1. 企业概况与核心指标\n"
        report += f"- **资产负债率**：{extracted_data['financials']['asset_liability_ratio']}%\n"
        report += f"- **流动比率**：{extracted_data['financials']['current_ratio']}\n"
        report += f"- **近期股权变更**：{'是' if extracted_data['business']['recent_equity_change'] else '否'}\n\n"
        
        report += "### 2. 规则校验风险清单\n"
        if not risk_results:
            report += "✅ 未发现明显命中风控规则的风险项。\n"
        else:
            for res in risk_results:
                icon = "🔴" if res["risk_level"] == "high" else "🟡"
                report += f"**{icon} 风险提示 ({res['rule_id']})**\n"
                report += f"- **详情**：{res['detail']}\n"
                report += f"- **系统建议**：{res['suggestion']}\n\n"
                
        report += "---\n*免责声明：本系统输出仅作为资料整理辅助，不构成信贷建议，所有结论需人工复核。*"
        
        return report

    def handle_query(self, query, current_data):
        """
        处理风控人员的追问，若配置了 LLM 则调用真实大模型，否则走 Mock 逻辑
        """
        if self.client and self.api_key:
            try:
                prompt = f"""
                你是一个专业的企业信贷风控助手。请基于以下企业提取数据回答用户的问题。
                
                [当前企业数据]
                {json.dumps(current_data, ensure_ascii=False, indent=2)}
                
                [用户问题]
                {query}
                
                请给出专业、客观、且符合金融合规要求的回答。不要替用户做放贷决策。
                """
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是 Horizon — 企业经营风险洞察助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"⚠️ LLM 调用失败（可能 API Key 无效或网络异常）：{str(e)}\n\n(已切换为降级回复) Agent 已收到您的指令，正在为您检索相关底层材料..."

        # 没有配置 LLM，走 Mock 逻辑
        time.sleep(1.0)
        if "涉诉案件详细" in query or "诉讼" in query:
            return "【Mock 回复】根据资料，该企业于2023年涉及一起买卖合同纠纷，作为被执行人，标的额为 150 万元人民币，目前案件状态为未结案。（如需体验智能回答，请在左侧配置大模型 API Key）"
        elif "过滤掉已结案" in query:
            return "【Mock 回复】已为您过滤已结案诉讼。重新校验后，上述 150 万元未结案诉讼风险依然存在。"
        elif "重新核算" in query and "流动比率" in query:
            return "【Mock 回复】已根据最新剔除预付账款的口径重新核算，速动比率为 0.8，流动性风险依然存在。"
        else:
            return "【Mock 回复】Agent 已收到您的指令，正在为您检索相关底层材料... (如需真实多轮对话能力，请配置大模型 API Key)"