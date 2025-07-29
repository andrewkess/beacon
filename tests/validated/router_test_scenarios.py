"""
Router test scenarios defined as Python constants.
This module replaces the JSON-based scenarios previously stored in router_test_scenarios.json.
"""

# Complex priority scenario
PRIORITY_SCENARIO = [
    {"role": "system", "content": "System: You are a helpful AI assistant."},
    {"role": "assistant", "content": "Hello! How can I assist you today?"},
    {"role": "user", "content": "Hi, I'm a researcher working in International Humanitarian Law. I'm trying to better understand France's involvement in armed conflicts around the world."},
    {"role": "assistant", "content": "That's an interesting research focus. I'd be happy to help you explore France's involvement in armed conflicts through the lens of International Humanitarian Law. Would you like to focus on a specific region or time period, or would you prefer a comprehensive overview?"},
    {"role": "user", "content": "I'd like a comprehensive overview first. Could you specifically identify which conflicts France is currently involved in as a state party, and the legal classification of those conflicts according to IHL?"},
    {"role": "assistant", "content": "I'd be happy to provide an overview of France's current involvement in armed conflicts as a state party and their legal classification under International Humanitarian Law.\n\nBased on available information, France is currently involved in several armed conflicts:\n\n1. In Syria - France is participating in the US-led coalition, which is classified as an International Armed Conflict (IAC) with Syria.\n\n2. In the Sahel region (Mali, Burkina Faso, Niger) - France has been engaged in counter-terrorism operations through Operation Barkhane, which would be classified as Non-International Armed Conflicts (NIACs).\n\n3. In Libya - France has provided support to various factions, which could be considered involvement in a NIAC.\n\n4. In the Central African Republic - France has provided military support to the government, which would be classified as a NIAC.\n\nIn each of these conflicts, different legal frameworks apply depending on the classification. Would you like me to elaborate on the specific legal obligations France has in any of these conflicts?"},
    {"role": "user", "content": "Yes, please focus on the Sahel region. Can you explain the legal obligations France has under IHL in this context, particularly considering they've been scaling back Operation Barkhane? Also, are there any recent developments regarding their legal status in Niger following the coup there?"},
    {"role": "assistant", "content": "Regarding France's legal obligations in the Sahel region under IHL:\n\n1. As a party to NIACs in the Sahel, France is bound by Common Article 3 of the Geneva Conventions, which establishes minimum standards for the treatment of non-combatants.\n\n2. France is also bound by customary international humanitarian law applicable to NIACs, including rules on the conduct of hostilities, protection of civilians, and treatment of detained persons.\n\n3. While scaling back Operation Barkhane, France maintains legal obligations for any military operations it conducts or supports in the region.\n\nRegarding Niger specifically, following the July 2023 coup:\n\n1. The military junta in Niger demanded the withdrawal of French forces.\n2. France initially refused to recognize the authority of the coup leaders.\n3. In December 2023, France announced the withdrawal of its troops from Niger, completing this process by the end of 2023.\n\nThis withdrawal has significantly altered France's legal position in Niger, as they no longer maintain a military presence there with the consent of the de facto authorities."},
    {"role": "user", "content": "That's very helpful. Let me shift focus a bit. Are any other European countries engaged in similar conflicts in that region?"}
]

# Scenario that asks for a report on a specific conflict, and provides details on format during a multi-turn conversation. so there should be several messages between user and assistant, essentially testing the conversational context extraction
SCENARIO_REPORT_ON_CONFLICT = [
    {"role": "user", "content": "I'm interested in the conflict in Ukraine. Can you provide a report on the current situation?"},
    {"role": "assistant", "content": "I'll help you understand the situation in Ukraine. The conflict began in 2014 and escalated significantly in February 2022 with Russia's full-scale invasion. Would you like me to focus on the current military situation, humanitarian impact, or legal classification of the conflict?"},
    {"role": "user", "content": "Let's start with the legal classification. How is this conflict categorized under international law?"},
    {"role": "assistant", "content": "The conflict in Ukraine is classified as an International Armed Conflict (IAC) between Russia and Ukraine. This classification triggers the full application of the Geneva Conventions and their Additional Protocols. The conflict also involves multiple dimensions, including occupation of certain territories. Would you like me to explain the specific legal frameworks that apply?"},
    {"role": "user", "content": "Yes, that's helpful. Can you also tell me about the humanitarian situation and civilian impact?"},
    {"role": "assistant", "content": "The humanitarian situation has been severe. Key impacts include: widespread civilian casualties, destruction of critical infrastructure, displacement of millions of civilians both internally and internationally, and disruption of essential services like healthcare and education. The UN has documented numerous violations of IHL, including attacks on civilian objects. Would you like specific details about humanitarian access and assistance efforts?"},
    {"role": "user", "content": "Yes, and could you also include information about international response and support?"},
    {"role": "assistant", "content": "The international response has been significant. NATO countries have provided military and humanitarian aid, with the EU implementing unprecedented sanctions against Russia. The UN and various humanitarian organizations have established extensive relief operations. Multiple international investigations are ongoing regarding alleged violations of IHL. The conflict has also impacted global food security due to Ukraine's role in grain exports. Shall I elaborate on any of these aspects?"},
    {"role": "user", "content": "This is very comprehensive. Could you summarize all these points in a structured report format?"}
]

# Web search scenario
WEB_SEARCH_SCENARIO = [
    {
        "role": "user", 
        "content": "is biden still president of the USA? who is the current president of the USA?"
    }
]

# Conflict classification scenario
SCENARIO_CONFLICT_CLASSIFICATION = [
    {"role": "assistant", "content": "Hello! How can I help you?"},
    {"role": "user", "content": "I'm curious about the conflict in Ukraine."},
    {
        "role": "assistant",
        "content": "Sure! Are you interested in classification or specific details?"
    },
    {
        "role": "user",
        "content": "Specifically, I'd like to know if it's an International or Non-International Armed Conflict, and maybe some background."
    }
]

# Single user message scenarios
SCENARIO_SINGLE_USER_MESSAGE1 = [
    {"role": "user", "content": "Could you write me a poem about dogs?"},
    {
        "role": "assistant",
        "content": "Dogs are blue, roses are red, don't be sad, dogs help you."
    },
    {"role": "user", "content": "Could you rewrite that, but just change the flower to violets? Sign it with today's date and time"}
]

SCENARIO_SINGLE_USER_MESSAGE2 = [
    {"role": "user", "content": "is france a state party to conflict?"}
]

# Basic knowledge scenarios
SCENARIO_BASIC_BEACON_KNOWLEDGE = [
    {"role": "user", "content": "What is international humanitarian law?"}
]

SCENARIO_BASIC_BEACON_SELF_KNOWLEDGE = [
    {"role": "user", "content": "Who are you? and what is your purpose? what tasks can you perform?"}
]

# Non-state actor conflict retrieval
SCENARIO_NON_STATE_ACTOR_CONFLICT_RETRIEVAL = [
    {"role": "user", "content": "what conflicts involve boko?"}
]

# Conflict by location scenario
SCENARIO_CONFLICT_TAKING_PLACE_IN_COUNTRY = [
    {"role": "user", "content": "what conflicts are taking place in Ukraine?"}
]

# Conflicts by organization tool
SCENARIO_CONFLICTS_BY_ORGANIZATION_TOOL = [
    {"role": "user", "content": "What IAC conflicts involve BRICS members?"}
]

# Task scenarios
TASK_SCENARIO_W_2_DIFF_TOOLS = [
    {"role": "user", "content": "Write a report that analyzes both france and russia's invovlement in NIAC conflict worldwide and the IHL that applies. one section should focus on france, one section should focus on russia, and the conclusion should compare the two countries' involvement to explore differences and similarities. Also add a small, separate section on the involvement of boko in africa."}
]

TASK_SCENARIO = [
    {"role": "user", "content": "Write a report that analyzes conflicts taking place in syria and ukraine."}
]

TASK_SCENARIO_W_EDIT = [
    {"role": "user", "content": "Write a report that analyzes frances invovlement in conflict worldwide and the IHL that applies."},
    {"role": "assistant", "content": "### France's Involvement in Armed Conflicts – RULAC Summary\n\nAccording to the **Rule of Law in Armed Conflict (RULAC)** project, France is currently involved in six distinct armed conflicts. Here is an overview of these conflicts:\n\n---\n\n### 1. Non-International Armed Conflicts in the Central African Republic\n\n**Overview:**  \nThe Central African Republic (CAR) is engaged in multiple non-international armed conflicts against various non-state actors, including ex-Séléka and anti-Balaka groups. The government is supported by the **United Nations Multidimensional Integrated Stabilization Mission (MINUSCA)**, Rwanda, the **Wagner Group**, and previously by France. Parallel conflicts also occur between different armed groups.\n\n**State Parties:**  \n- **France, Rwanda, Central African Republic**\n\n**Non-State Parties:**  \n- **Anti-Balaka Armed Group**  \n- **Central African Liberators for Justice Movement (MLCJ)**  \n- **Union for Peace in the Central African Republic (UPC)**  \n- **Popular Front for the Renaissance in the Central African Republic (FPRC)**  \n- **Return, Reclamation, and Rehabilitation (3R)**  \n- **Séléka/Ex-Séléka Coalition Group**  \n- **Central African Patriotic Movement (MPC)**  \n- **United Nations Multidimensional Integrated Mission (MINUSCA)**  \n\n---\n\n### 2. Non-International Armed Conflicts in Niger\n\n**Overview:**  \nNiger faces several non-international armed conflicts, particularly against **Boko Haram** and the **Islamic State in West Africa Province (ISWAP)**. The **Multinational Joint Task Force (MNJTF)**, comprising units from Nigeria, Niger, Chad, Cameroon, and Benin, is active against Boko Haram. French forces have been present in Niger since July 2022, supporting the government.\n\n**State Parties:**  \n- **France, Niger**\n\n**Non-State Parties:**  \n- **ISWAP**  \n- **Boko Haram**  \n- **Multinational Joint Task Force (MNJTF)**  \n\n---\n\n### 3. International Armed Conflicts in Syria\n\n**Overview:**  \nSyria is involved in multiple international armed conflicts against the **US-led coalition**, **Türkiye**, and **Israel**. Türkiye occupies parts of northern Syria, while Israel occupies the **Golan Heights**. The US-led coalition, including France, conducts military operations in Syria.\n\n**State Parties:**  \n- **France, Netherlands, Italy, Belgium, Germany, UAE, Israel, Denmark, UK, Australia, Türkiye, Saudi Arabia, Jordan, Syrian Arab Republic, USA**\n\n**Non-State Parties:**  \n- **None recorded**  \n\n---\n\n### 4. Non-International Armed Conflicts in Burkina Faso\n\n**Overview:**  \nBurkina Faso is engaged in multiple non-international armed conflicts against jihadist groups, including **Ansaroul Islam**, **ISWAP**, **Islamic State in the Greater Sahara (ISGS)**, and the **Group for the Support of Islam and Muslims (JNIM)**. France has been militarily active in Burkina Faso since 2014 through **Operation Barkhane**.\n\n**State Parties:**  \n- **France, Burkina Faso**\n\n**Non-State Parties:**  \n- **ISGS**  \n- **JNIM**  \n- **ISWAP**  \n- **Ansaroul Islam**  \n\n---\n\n### 5. Non-International Armed Conflicts in Syria\n\n**Overview:**  \nSyria is also involved in multiple non-international armed conflicts against rebel groups, including the **Syrian National Army**, **Hay'at Tahrir al-Sham**, the **Islamic State group**, and the **Syrian Democratic Forces**. Foreign state forces, including France, are involved against armed groups on Syrian territory.\n\n**State Parties:**  \n- **France, Netherlands, Belgium, Germany, UAE, UK, Australia, Türkiye, Saudi Arabia, Jordan, Syrian Arab Republic, USA, Russian Federation**\n\n**Non-State Parties:**  \n- **Islamic State group**  \n- **Hezbollah**  \n- **Syrian Democratic Forces (including YPG)**  \n- **Ahrar al-Sham**  \n- **Hay'at Tahrir al-Sham**  \n- **Syrian National Army (SNA)**  \n- **Former Free Syrian Army (FSA)**  \n\n---\n\n### 6. Non-International Armed Conflicts in Libya\n\n**Overview:**  \nLibya has been in political unrest and armed violence since the fall of the Qaddafi regime in 2011. Multiple non-international armed conflicts involve the **Government of Libya**, the **Libyan National Army (LNA)**, various armed groups, and foreign powers. France and the **United Arab Emirates** support the LNA.\n\n**State Parties:**  \n- **France, UAE, Türkiye, USA, Libya**\n\n**Non-State Parties:**  \n- **Islamic State group**  \n- **Libyan National Army**  \n- **Derna Protection Force (DPF)**  \n- **Benghazi Revolutionaries Shura Council (BRSC)**  \n\n---\n\n### Applicable International Humanitarian Law (IHL)\n\nIn all these conflicts, the parties are bound by:  \n- **Article 3 common to the 1949 Geneva Conventions**, which sets minimum standards for humane treatment and prohibits:  \n  - **Murder, Mutilation, Torture, Cruel Treatment, Hostage-Taking, and Unfair Trials**.  \n- **Customary International Humanitarian Law** and **International Human Rights Law**, obligating states to **prevent and investigate alleged violations**."},
    {"role": "user", "content": "can you edit that report by focusing on just the IHL?"}
]

# RULAC tool test scenarios
SCENARIO_RULAC_CONFLICT_BY_REGION_TOOL_TEST = [
    {"role": "user", "content": "how many conflicts in europe?"}
]

SCENARIO_RULAC_IHL_LEGAL_FRAMEWORK = [
    {"role": "user", "content": "What is the International Humanitarian Law legal framework? How does it apply to armed conflicts?"}
]

SCENARIO_RULAC_CONFLICT_CLASSIFICATION = [
    {"role": "user", "content": "How does RULAC classify armed conflicts? What methodology do they use to determine if a situation is an armed conflict?"}
]

SCENARIO_RULAC_GENERAL_INFORMATION = [
    {"role": "user", "content": "What is RULAC? What is the purpose of RULAC research?"}
]

# Multi-tool scenarios
SCENARIO_TWO_TOOLS_W_IHL_LEGAL_FRAMEWORK = [
    {"role": "user", "content": "What conflicts are France involved in and what is the International Humanitarian Law legal framework? How does it apply to these specific armed conflicts?"}
]

SCENARIO_TWO_TOOLS_W_IHL_LEGAL_FRAMEWORK_2 = [
    {"role": "user", "content": "What conflicts is Russia and the USA involved in and what IHL applies? what is the methodology used to classify them?"}
]

# Multi-turn conversation scenarios
SCENARIO_MULTITURN_USER_TASK = [
    {"role": "system", "content": "System: You are a helpful AI assistant."},
    {"role": "assistant", "content": "Hello! How can I assist you today?"},
    {"role": "user", "content": "I need some information on international humanitarian law."},
    {"role": "assistant", "content": "Sure, what specific information are you looking for?"},
    {"role": "user", "content": "Can you tell me about the Geneva Conventions?"},
    {"role": "assistant", "content": "The Geneva Conventions are a set of treaties on the treatment of civilians, prisoners of war, and soldiers who are otherwise rendered hors de combat, or incapable of fighting. Do you need details on a specific convention?"},
    {"role": "user", "content": "Yes, please provide details on the Third Geneva Convention."},
    {"role": "assistant", "content": "The Third Geneva Convention primarily deals with the treatment of prisoners of war. It defines their rights and sets down detailed rules for their treatment and eventual release. Is there anything specific you would like to know about it?"},
    {"role": "user", "content": "I need to write a report on how the Third Geneva Convention applies to current conflicts. Can you help with that?"},
    {"role": "assistant", "content": "Absolutely, I can help with that. Do you have any specific conflicts in mind?"},
    {"role": "user", "content": "Yes, I am interested in the application of the Third Geneva Convention in the context of the conflict in Syria."}
]

# Topic switching scenario
SCENARIO_SWITCHED_TOPIC = [
    {"role": "system", "content": "System: You are a helpful AI assistant."},
    {"role": "assistant", "content": "How can I help you today?"},
    {"role": "user", "content": "Tell me about the conflict in Ukraine."},
    {"role": "assistant", "content": "Sure. What aspect of the conflict?"},
    {
        "role": "user",
        "content": "Actually, never mind. I'd like some tips on home gardening instead."
    }
]

# Human rights scenario
SCENARIO_HUMAN_RIGHTS = [
    {"role": "system", "content": "System: You are a helpful AI assistant."},
    {
        "role": "assistant",
        "content": "Welcome! How may I assist you?"
    },
    {
        "role": "user",
        "content": "Explain the Universal Declaration of Human Rights."
    }
]

# Irrelevant query scenario
SCENARIO_IRRELEVANT = [
    {"role": "system", "content": "System: You are an AI assistant."},
    {"role": "assistant", "content": "Hello!"},
    {"role": "user", "content": "How do I fix my phone screen?"}
]

# Date and time test scenario
SCENARIO_TEST_TIME = [
    {"role": "user", "content": "how many conflicts is france actively involved in? write a 2 paragraph report and include today's date and time."}
]

# Website request scenario
SCENARIO_GET_WEBSITE = [
    {"role": "user", "content": "Can you get the latest news on this website: bbc.com. anything about the conflict in Ukraine? how is it classified?"}
]

# Testing that BeaconAgent is not being used
SCENARIO_BEACON_AGENT_NOT_USED = [
    {"role": "user", "content": "are there more IACs in Europe or Asia?"}
]

# Dictionary mapping scenario names to their constants
TEST_SCENARIOS = {
    "beacon_agent_not_used": SCENARIO_BEACON_AGENT_NOT_USED,
    # "report_on_conflict": SCENARIO_REPORT_ON_CONFLICT,
    "priority_scenario": PRIORITY_SCENARIO,
    # "web_search_scenario": WEB_SEARCH_SCENARIO,
    # "scenario_conflict_classification": SCENARIO_CONFLICT_CLASSIFICATION,
    # "scenario_single_user_message1": SCENARIO_SINGLE_USER_MESSAGE1,
    # # "scenario_single_user_message2": SCENARIO_SINGLE_USER_MESSAGE2,
    "scenario_basic_beacon_knowledge": SCENARIO_BASIC_BEACON_KNOWLEDGE,
    # "scenario_basic_beacon_self_knowledge": SCENARIO_BASIC_BEACON_SELF_KNOWLEDGE,
    # "scenario_non_state_actor_conflict_retrieval": SCENARIO_NON_STATE_ACTOR_CONFLICT_RETRIEVAL,
    # # "scenario_conflict_taking_place_in_country": SCENARIO_CONFLICT_TAKING_PLACE_IN_COUNTRY,
    # "scenario_conflicts_by_organization_tool": SCENARIO_CONFLICTS_BY_ORGANIZATION_TOOL,
    # "task_scenario_w_2_diff_tools": TASK_SCENARIO_W_2_DIFF_TOOLS,
    # "task_scenario": TASK_SCENARIO,
    # "task_scenario_w_edit": TASK_SCENARIO_W_EDIT,
    # "scenario_rulac_conflict_by_region_tool_test": SCENARIO_RULAC_CONFLICT_BY_REGION_TOOL_TEST,
    # "scenario_rulac_ihl_legal_framework": SCENARIO_RULAC_IHL_LEGAL_FRAMEWORK,
    # "scenario_rulac_conflict_classification": SCENARIO_RULAC_CONFLICT_CLASSIFICATION,
    # "scenario_rulac_general_information": SCENARIO_RULAC_GENERAL_INFORMATION,
    # "scenario_two_tools_w_IHL_legal_framework": SCENARIO_TWO_TOOLS_W_IHL_LEGAL_FRAMEWORK,
    # "scenario_two_tools_w_IHL_legal_framework_2": SCENARIO_TWO_TOOLS_W_IHL_LEGAL_FRAMEWORK_2,
    # "scenario_multiturn_user_task": SCENARIO_MULTITURN_USER_TASK,
    # "scenario_switched_topic": SCENARIO_SWITCHED_TOPIC,
    # "scenario_human_rights": SCENARIO_HUMAN_RIGHTS,
    # "scenario_irrelevant": SCENARIO_IRRELEVANT,
    # "scenario_test_time": SCENARIO_TEST_TIME,
    # "scenario_get_website": SCENARIO_GET_WEBSITE
} 