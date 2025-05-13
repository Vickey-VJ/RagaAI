import os
import re
import json # ADDED for LLM interaction
import requests # ADDED for LLM interaction
from dotenv import load_dotenv

# Define keyword lists for analysis
RISK_KEYWORDS = [
    "volatility", "volatile", "uncertainty", "uncertain", "risk", "risks", "risky",
    "decline", "drop", "fall", "decrease", "slump", "downturn", "contraction",
    "regulatory scrutiny", "regulatory action", "investigation", "lawsuit", "litigation",
    "geopolitical tension", "geopolitical risk", "trade war", "sanctions",
    "supply chain disruption", "supply chain issue", "shortage",
    "economic downturn", "recession", "inflationary pressure", "interest rate hike",
    "cybersecurity threat", "data breach", "hack",
    "competition", "competitive pressure", "market share loss",
    "bearish", "headwinds", "challenge", "challenges", "concern", "concerns",
    "significant drop", "sharp fall", "warning", "alert"
]

EARNINGS_POSITIVE_KEYWORDS = [
    "earnings beat estimates", "beat estimates", "exceeded expectations", "strong results", 
    "better-than-expected", "record profit", "record revenue", "strong growth", 
    "guidance raised", "raised guidance", "upgraded guidance", "positive outlook",
    "outperform", "surpassed", "jump in profit", "revenue surge"
]

EARNINGS_NEGATIVE_KEYWORDS = [
    "earnings missed estimates", "missed estimates", "fell short of expectations", "weak results",
    "worse-than-expected", "profit warning", "guidance lowered", "lowered guidance",
    "downgraded guidance", "negative outlook", "underperform", "failed to meet",
    "drop in profit", "revenue decline", "loss reported"
]

EARNINGS_NEUTRAL_KEYWORDS = [
    "reaffirmed guidance", "in line with expectations", "met expectations", 
    "guidance unchanged", "mixed results"
]

# These lists might be deprecated or used as a fallback if LLM call fails
EARNINGS_GENERAL_TERMS = [
    "earnings", "profit", "revenue", "net income", "eps", "margin", "margins",
    "income before taxes", "operating income", "gross profit", "sales", "turnover"
]
VERBS_INCREASE = [
    "increase", "increases", "increased", "grew", "grow", "grows", "rose", "rise", "rises", 
    "expand", "expands", "expanded", "improve", "improves", "improved", "surged", "jumped", 
    "beat", "exceeded", "higher", "stronger", "up", "accelerated", "advanced"
]
VERBS_DECREASE = [
    "decrease", "decreases", "decreased", "fell", "fall", "falls", "shrank", "shrink", "shrinks", 
    "contract", "contracts", "contracted", "reduced", "reduce", "reduces", "declined", "decline", "declines", 
    "dropped", "missed", "lower", "weaker", "down", "slowed", "softened"
]

class AnalysisAgent:
    def __init__(self):
        print("Initializing AnalysisAgent...")
        self.language_service_url = os.getenv("LANGUAGE_SERVICE_URL", "http://localhost:8003") # ADDED
        if not self.language_service_url.startswith("http"):
            self.language_service_url = "http://" + self.language_service_url
        print(f"AnalysisAgent configured with Language Service URL: {self.language_service_url}")

    def _call_language_service(self, prompt: str) -> dict | None: # ADDED Helper
        try:
            response = requests.post(
                f"{self.language_service_url}/language/generate",
                json={"prompt": prompt},
                timeout=45 # Increased timeout for LLM calls
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"AnalysisAgent: Error calling LanguageService: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"AnalysisAgent: Error decoding JSON from LanguageService: {e}")
            return None

    def _extract_relevant_snippets(self, text: str, keywords: list[str], window=100) -> list[str]:
        """Helper to extract snippets around keywords."""
        snippets = []
        text_lower = text.lower()
        for keyword in keywords:
            try:
                # Use regex to find whole word matches for keywords to avoid partial matches
                # This regex looks for the keyword bounded by non-alphanumeric characters or start/end of string
                for match in re.finditer(r'(?:^|\W)' + re.escape(keyword.lower()) + r'(?:$|\W)', text_lower):
                    start, end = match.start(), match.end()
                    # Adjust start/end to be around the keyword itself, not the non-alphanumeric boundary
                    kw_start = text_lower.find(keyword.lower(), start)
                    kw_end = kw_start + len(keyword)
                    
                    snippet_start = max(0, kw_start - window)
                    snippet_end = min(len(text), kw_end + window)
                    snippets.append(f"...{text[snippet_start:snippet_end]}...")
            except re.error as e:
                print(f"Regex error for keyword '{keyword}': {e}")
                # Fallback to simple string finding if regex fails for a specific keyword
                idx = text_lower.find(keyword.lower())
                if idx != -1:
                    snippet_start = max(0, idx - window)
                    snippet_end = min(len(text), idx + len(keyword) + window)
                    snippets.append(f"...{text[snippet_start:snippet_end]}...")
        return list(set(snippets)) # Return unique snippets

    def analyze_market_data(self, market_info: dict | None, news_articles: list[str], company_filings: list[str], company_ticker: str | None = None) -> dict:
        """
        Analyzes a combination of market information, news, and filings
        to identify insights, risks, or surprises.

        Args:
            market_info (dict | None): e.g., stock data from APIAgent. 
                                     Example: {"symbol": "AAPL", "price": 150.00, "change_percent": "-1.5%"}
            news_articles (list[str]): Relevant news snippets/full articles.
            company_filings (list[str]): Relevant excerpts/full documents from company filings.
            company_ticker (str | None): The primary company ticker for focused analysis.

        Returns:
            dict: Analysis results.
        """
        ticker_to_analyze = company_ticker or (market_info.get('symbol') if market_info else 'N/A')
        print(f"AnalysisAgent received data for: {ticker_to_analyze}")
        print(f"AnalysisAgent received {len(news_articles)} news articles and {len(company_filings)} filing excerpts.")

        identified_risks = []
        all_texts = news_articles + company_filings

        # 1. Identify risks from text
        for text_content in all_texts:
            risk_snippets = self._extract_relevant_snippets(text_content, RISK_KEYWORDS)
            for snippet in risk_snippets:
                identified_risks.append({
                    "source_type": "text_analysis",
                    "description": "Potential risk factor mentioned.",
                    "evidence": snippet,
                    "keywords_found": [kw for kw in RISK_KEYWORDS if kw in snippet.lower()]
                })
        
        # 2. Identify risks from market_info (e.g., significant price drop)
        if market_info and 'change_percent' in market_info:
            try:
                change_str = market_info['change_percent'].replace('%', '')
                percent_change = float(change_str)
                if percent_change < -5.0: # Arbitrary threshold for significant drop
                    identified_risks.append({
                        "source_type": "market_data",
                        "description": f"Significant price drop of {market_info['change_percent']}.",
                        "evidence": f"Symbol: {market_info.get('symbol', 'N/A')}, Change: {market_info['change_percent']}",
                        "keywords_found": ["significant drop"]
                    })
            except ValueError:
                print(f"Could not parse percent_change: {market_info['change_percent']}")


        # 3. Find earnings surprises
        earnings_analysis_results = self.find_earnings_surprises(all_texts, ticker_to_analyze)

        # Deduplicate risks based on evidence snippet to avoid too much redundancy
        unique_risks = []
        seen_evidence = set()
        for risk in identified_risks:
            if risk["evidence"] not in seen_evidence:
                unique_risks.append(risk)
                seen_evidence.add(risk["evidence"])
        
        analysis_summary = f"Analysis for {ticker_to_analyze}: Found {len(unique_risks)} potential risk(s). Earnings analysis indicates: {earnings_analysis_results.get('summary_status', 'N/A')}."
        
        return {
            "ticker_analyzed": ticker_to_analyze,
            "identified_risks": unique_risks,
            "earnings_analysis": earnings_analysis_results,
            "summary": analysis_summary,
            "raw_data_refs": {
                "news_count": len(news_articles),
                "filings_count": len(company_filings),
                "market_info_present": bool(market_info)
            }
        }

    def find_earnings_surprises(self, text_snippets: list[str], company_ticker: str) -> dict:
        print(f"AnalysisAgent attempting to find earnings surprises for {company_ticker} in {len(text_snippets)} snippets.")
        
        surprises = []
        positive_mentions = 0
        negative_mentions = 0
        neutral_mentions = 0

        for snippet_text in text_snippets:
            positive_found_keywords = [kw for kw in EARNINGS_POSITIVE_KEYWORDS if re.search(r'(?:^|\W)' + re.escape(kw.lower()) + r'(?:$|\W)', snippet_text.lower())]
            if positive_found_keywords:
                extracted_snips = self._extract_relevant_snippets(snippet_text, positive_found_keywords)
                for es in extracted_snips:
                    surprises.append({"type": "positive", "evidence": es, "keywords": positive_found_keywords})
                positive_mentions += len(extracted_snips)

            negative_found_keywords = [kw for kw in EARNINGS_NEGATIVE_KEYWORDS if re.search(r'(?:^|\W)' + re.escape(kw.lower()) + r'(?:$|\W)', snippet_text.lower())]
            if negative_found_keywords:
                extracted_snips = self._extract_relevant_snippets(snippet_text, negative_found_keywords)
                for es in extracted_snips:
                    surprises.append({"type": "negative", "evidence": es, "keywords": negative_found_keywords})
                negative_mentions += len(extracted_snips)
            
            if not positive_found_keywords and not negative_found_keywords: # Only check neutral if no pos/neg explicit keywords found in this snippet
                neutral_found_keywords = [kw for kw in EARNINGS_NEUTRAL_KEYWORDS if re.search(r'(?:^|\W)' + re.escape(kw.lower()) + r'(?:$|\W)', snippet_text.lower())]
                if neutral_found_keywords:
                    extracted_snips = self._extract_relevant_snippets(snippet_text, neutral_found_keywords)
                    for es in extracted_snips:
                        surprises.append({"type": "neutral", "evidence": es, "keywords": neutral_found_keywords})
                    neutral_mentions += len(extracted_snips)
        
        unique_surprises = []
        seen_surprise_evidence = set()
        for surprise in surprises:
            if surprise["evidence"] not in seen_surprise_evidence:
                unique_surprises.append(surprise)
                seen_surprise_evidence.add(surprise["evidence"])

        confidence = "low"
        summary_status = "No clear earnings surprise signal found by keyword matching." 

        if positive_mentions > 0 and positive_mentions > negative_mentions:
            confidence = "medium" if positive_mentions < 3 else "high"
            summary_status = "Potential positive earnings surprise detected based on explicit keywords."
        elif negative_mentions > 0 and negative_mentions > positive_mentions:
            confidence = "medium" if negative_mentions < 3 else "high"
            summary_status = "Potential negative earnings surprise detected based on explicit keywords."
        elif neutral_mentions > 0 and positive_mentions == 0 and negative_mentions == 0:
            confidence = "low"
            summary_status = "Neutral earnings-related statements detected (e.g., guidance reaffirmed) by explicit keywords."
        elif positive_mentions == 0 and negative_mentions == 0: # If no explicit positive or negative surprises, try LLM
            print(f"AnalysisAgent: No explicit surprise keywords for {company_ticker}. Attempting LLM analysis.")
            # Combine snippets for LLM, ensuring not too long. Max ~3000 words for safety.
            # A more robust solution would handle token limits more gracefully.
            combined_text = "\n\n---\n\n".join(text_snippets)
            max_words = 3000 
            word_list = combined_text.split()
            if len(word_list) > max_words:
                print(f"AnalysisAgent: Combined text too long ({len(word_list)} words), truncating for LLM.")
                combined_text = " ".join(word_list[:max_words])

            llm_prompt = (
                f"Analyze the following text snippets concerning company {company_ticker} and its recent earnings. "
                f"Determine the overall earnings sentiment or trend. Focus on whether the information suggests "
                f"positive, negative, or neutral earnings performance, or specific surprises like beating/missing estimates. "
                f"If specific surprise language isn't present, describe the general trend (e.g., 'revenue growth', 'profit decline').\n\n"
                f"Respond with a short summary (1-2 sentences) of the earnings sentiment/trend. For example: \n"
                f"- '{company_ticker} reported strong earnings, beating estimates due to X.'\n"
                f"- 'Earnings for {company_ticker} were weak, missing expectations and showing a decline in Y.'\n"
                f"- '{company_ticker} showed revenue growth but declining profits, a mixed signal.'\n"
                f"- 'Neutral earnings for {company_ticker}, in line with expectations.'\n"
                f"- 'The text indicates positive earnings trends for {company_ticker} with revenue up.'\n"
                f"- 'The text suggests negative earnings trends for {company_ticker} with margins shrinking.'\n"
                f"- 'No clear earnings trend or surprise identified for {company_ticker} from the text.'\n\n"
                f"Text Snippets:\n---\n{combined_text}\n---\n"
                f"Your concise summary of earnings sentiment/trend for {company_ticker}:"
            )
            
            llm_response_data = self._call_language_service(llm_prompt)
            
            if llm_response_data and llm_response_data.get("response"):
                llm_summary = llm_response_data["response"].strip()
                summary_status = f"LLM analysis: {llm_summary}"
                # Attempt to infer confidence from LLM response (simple version)
                if "strong" in llm_summary.lower() or "beat estimates" in llm_summary.lower() or "exceeded" in llm_summary.lower():
                    confidence = "medium" # Could be high if LLM is very explicit
                elif "weak" in llm_summary.lower() or "missed estimates" in llm_summary.lower() or "decline" in llm_summary.lower():
                    confidence = "medium"
                elif "neutral" in llm_summary.lower() or "in line" in llm_summary.lower():
                    confidence = "low"
                else: # General trend
                    confidence = "low" 
                print(f"AnalysisAgent: LLM analysis for {company_ticker} complete. Status: {summary_status}, Confidence: {confidence}")
            else:
                summary_status = "LLM analysis for earnings failed or returned no response. Falling back to basic check."
                # Fallback to the previous general term check if LLM fails
                general_earnings_terms_actually_present = False
                for snippet_text_original in text_snippets: 
                    text_lower = snippet_text_original.lower()
                    if any(term in text_lower for term in EARNINGS_GENERAL_TERMS):
                        general_earnings_terms_actually_present = True
                        break
                if general_earnings_terms_actually_present:
                    summary_status = "Earnings-related information was present, but no explicit surprise statements or clear directional verb indicators were detected by keyword matching (LLM call failed)."
                else:
                    summary_status = "No specific earnings-related statements (including surprises or general terms) were detected by keyword matching (LLM call failed)."
        
        return {
            "ticker": company_ticker,
            "potential_surprises": unique_surprises, # Still based on explicit keywords
            "confidence": confidence,
            "summary_status": summary_status
        }

if __name__ == '__main__':
    # Ensure .env is loaded for direct testing if LANGUAGE_SERVICE_URL is needed
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if (os.path.exists(dotenv_path)):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded .env from {dotenv_path} for AnalysisAgent direct test.")
    else:
        print(f".env file not found at {dotenv_path}. LANGUAGE_SERVICE_URL might not be set for direct test.")

    agent = AnalysisAgent()
    
    print("\n--- Test Case 1: General Analysis (AAPL) ---")
    sample_news_aapl = [
        "Market sees increased volatility. Apple Inc. (AAPL) stock dropped 6% today amid tech sector sell-off.",
        "New report highlights supply chain issues for major tech manufacturers, including Apple.",
        "Apple Q2 earnings beat estimates, revenue surged by 15% due to strong iPhone sales. Guidance raised for next quarter."
    ]
    sample_filings_aapl = [
        "Our company faces significant competition and regulatory scrutiny in several key markets.",
        "Forward-looking statements: We expect continued headwinds in the European market due to economic downturn."
    ]
    sample_market_info_aapl = {"symbol": "AAPL", "price": 140.00, "change_percent": "-6.0%"}

    results_aapl = agent.analyze_market_data(sample_market_info_aapl, sample_news_aapl, sample_filings_aapl, company_ticker="AAPL")
    print(f"AAPL General Analysis Results:")
    print(f"  Ticker: {results_aapl['ticker_analyzed']}")
    print(f"  Summary: {results_aapl['summary']}")
    print(f"  Identified Risks ({len(results_aapl['identified_risks'])}):")
    for risk in results_aapl['identified_risks'][:2]: # Print first 2 risks
        print(f"    - {risk['description']} Evidence: {risk['evidence'][:100]}... Keywords: {risk['keywords_found']}")
    print(f"  Earnings Analysis:")
    print(f"    Status: {results_aapl['earnings_analysis']['summary_status']}")
    print(f"    Confidence: {results_aapl['earnings_analysis']['confidence']}")
    for surprise in results_aapl['earnings_analysis']['potential_surprises'][:2]: # Print first 2 surprises
        print(f"      - Type: {surprise['type']}, Evidence: {surprise['evidence'][:100]}... Keywords: {surprise['keywords']}")

    print("\n--- Test Case 2: Earnings Surprise Focus (TechCorp) ---")
    sample_texts_techcorp = [
        "TechCorp (TCORP) Q1 earnings missed estimates significantly. CEO cited unexpected market challenges.",
        "Analysts are concerned after TechCorp lowered its guidance for the full year.",
        "Despite the recent profit warning, some see long-term value in TCORP."
    ]
    results_techcorp_earnings = agent.find_earnings_surprises(sample_texts_techcorp, "TCORP")
    print(f"TechCorp Earnings Surprise Analysis:")
    print(f"  Ticker: {results_techcorp_earnings['ticker']}")
    print(f"  Status: {results_techcorp_earnings['summary_status']}")
    print(f"  Confidence: {results_techcorp_earnings['confidence']}")
    for surprise in results_techcorp_earnings['potential_surprises']:
        print(f"    - Type: {surprise['type']}, Evidence: {surprise['evidence'][:100]}... Keywords: {surprise['keywords']}")

    print("\n--- Test Case 3: No Clear Signals, LLM to Analyze (XYZ) ---")
    sample_texts_xyz = [
        "XYZ Corp reported earnings for the third quarter. Revenue was up slightly but profits were flat.",
        "The company mentioned that overall sales volume for core products saw a modest increase.",
        "Market conditions remain stable for XYZ's sector, though some input costs have risen."
    ]
    results_xyz_earnings = agent.find_earnings_surprises(sample_texts_xyz, "XYZ")
    print(f"XYZ Corp Earnings Surprise Analysis (LLM assist):")
    print(f"  Ticker: {results_xyz_earnings['ticker']}")
    print(f"  Status: {results_xyz_earnings['summary_status']}")
    print(f"  Confidence: {results_xyz_earnings['confidence']}")
    # Potential surprises list will be empty if LLM path was taken and no explicit keywords were found
    for surprise in results_xyz_earnings['potential_surprises']:
        print(f"    - Type: {surprise['type']}, Evidence: {surprise['evidence'][:100]}... Keywords: {surprise['keywords']}")
    
    print("\n--- Test Case 4: Only Risk, No Earnings News, LLM Fallback (RISKCO) ---")
    sample_news_riskco = [
        "RISKCO is under investigation by regulatory bodies for alleged market manipulation.",
        "The company's stock has seen increased volatility over the past month.",
        "A recent cybersecurity threat was identified and neutralized by RISKCO. No mention of quarterly financial results."
    ]
    results_riskco_earnings = agent.find_earnings_surprises(sample_news_riskco, "RISKCO")
    print(f"RISKCO Earnings Surprise Analysis (LLM assist for no earnings news):")
    print(f"  Ticker: {results_riskco_earnings['ticker']}")
    print(f"  Status: {results_riskco_earnings['summary_status']}")
    print(f"  Confidence: {results_riskco_earnings['confidence']}")

    print("\n--- AnalysisAgent Test Complete ---")
