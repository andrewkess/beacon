import json
import random

# Define your list of questions with a placeholder for each country.
questions_for_each_country = [
    {
        "category": "1. EACH COUNTRY Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) Involving a single State Actor",
        "questions": [
            "What conflicts is the state actor xStateActor involved in?",
            "What conflicts is xStateActor involved in?",
            "What IHL applies to the conflicts involving xStateActor as a state actor?",
            "How does international humanitarian law classify conflicts involving xStateActor as a state actor?"
        ]
    },
            {
      "category": "6. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single Country",
        "questions": [
          "What conflicts are taking place in xStateActor?",
          "What is the IHL that applies to the conflicts taking place in xStateActor?",
        ]
    },  
]

# Define your list of questions with a placeholder for a random country.
questions_for_random_country = [
    {
        "category": "1. RANDOM COUNTRY Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) Involving a single State Actor",
        "questions": [
            "How many conflicts is xStateActor actively engaged in?",
            "Is the country xStateActor involved in any conflict?",
            "Is xStateActor a party to conflict?",
            "Which conflicts is xStateActor involved in as a state party?",
            "How many conflicts is xStateActor involved in? What are their names?",
            "What conflicts is xStateActor currently participating in as a state actor?",
            "How many conflicts is xStateActor involved in, and what are their classifications?",
            "Has xStateActor been involved in any armed conflicts?",
            "Which conflicts has xStateActor participated in as a state party, and who are the opposing actors?",
            "Has xStateActor been engaged in any recognized armed conflicts in recent years?",
            "What are the legal classifications of conflicts involving xStateActor as a state actor?",
            "How to classify xStateActor conflicts or conflicts involving xStateActor?",
            "What is the classification of conflicts involving the state actor xStateActor?",
            "Which IHL provisions apply to conflicts involving xStateActor?",
            "Which international treaties govern the conflicts involving the state actor xStateActor, i.e IHL law?",
            "What legal frameworks apply to conflicts involving xStateActor as a state actor?"
        ]
    },
    {
        "category": "2. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) Involving a single State Actor WITH conflict classification FILTER",
        "questions": [
            "What IAC conflicts is the state actor xStateActor involved in?",
            "What NIAC conflicts is the state actor xStateActor involved in?",
            "What military occupations is the state actor xStateActor involved in?",
            "What IAC and NIAC conflicts is the state actor xStateActor involved in?",
            "What NIAC or IAC conflicts is xStateActor involved in?",
            "How many NIACs is xStateActor actively engaged in?",
            "Is the country xStateActor involved in any NIAC conflict?",
            "Is xStateActor a party to any NIACs?",
            "Which non-international armed conflicts is xStateActor involved in as a state party?",
            "How many non-international armed conflicts is xStateActor involved in? What are their names?",
            "What non-international armed conflicts is xStateActor currently participating in as a state actor?",
            "How many NIACs is xStateActor involved in, and what are their classifications?",
            "Has xStateActor been involved in any NIAC conflicts?",
            "Which NIACs has xStateActor participated in as a state party, and who are the opposing actors?",
            "Has xStateActor been engaged in any recognized NIACs conflicts in recent years?",
            "What are the legal classifications of NIAC conflicts involving xStateActor as a state actor?",
            "What IHL applies to the NIACs involving xStateActor as a state actor?",
            "Which IHL provisions apply to NIACs involving xStateActor?",
            "How does international humanitarian law classify NIACs involving xStateActor as a state actor?",
            "Which international treaties govern the NIACs involving the state actor xStateActor, i.e IHL law?",
            "What legal frameworks apply to NIACs involving xStateActor as a state actor?"
        ]
    },
        {
      "category": "6. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single Country",
        "questions": [
          "How many conflicts are taking place in xStateActor?",
          "Are there any conflicts taking place in xStateActor?",
          "Which conflicts are taking place in xStateActor?",
          "What are the classifications of the conflicts taking place in xStateActor?",
          "What is the legal framework involving the conflicts taking place in xStateActor?"
        ]
    },    
      {
        "category": "7. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single Country WITH conflict classification FILTER",
        "questions": [
          "What IAC conflicts are taking place in xStateActor?",
          "What NIAC conflicts are taking place in xStateActor?",
          "What military occupations are taking place in xStateActor?",
          "What IAC and NIAC conflicts are taking place in xStateActor?",
          "How many NIACs are taking place in xStateActor?",
          "Which non-international armed conflicts are taking place in xStateActor?",
          "How many non-international armed conflicts are taking place in xStateActor? What are their names?",
          "Which IACs are taking place in xStateActor, and who are the opposing actors?",
          "What are the legal classifications of NIAC conflicts taking place in xStateActor?",
          "What IHL applies to the IACs taking place in xStateActor?",
          "Which IHL provisions apply to IACs inside xStateActor?",
          "How does international humanitarian law classify conflicts in xStateActor?",
          "Which international treaties govern the NIACs taking place in xStateActor, i.e IHL law?",
          "What legal frameworks apply to NIACS taking place in xStateActor?"
        ]
      },
]

# Define your list of questions with placeholders for 2 random countries.
questions_for_random_two_countries = [
    {
        "category": "3. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) Involving MULTIPLE State Actors",
        "questions": [
            "What conflicts is the state actor xStateActor and yStateActor involved in?",
            "What conflicts is xStateActor and yStateActor involved in?",
            "How many conflicts is xStateActor and yStateActor actively engaged in?",
            "Is the country xStateActor or yStateActor involved in any conflict?",
            "Is xStateActor or yStateActor a party to conflict?",
            "Which conflicts is xStateActor and yStateActor involved in as a state party?",
            "How many conflicts is xStateActor or yStateActor involved in? What are their names?",
            "What conflicts is xStateActor or yStateActor currently participating in as a state actor?",
            "How many conflicts is xStateActor or yStateActor involved in, and what are their classifications?",
            "Has xStateActor or yStateActor been involved in any armed conflicts?",
            "Which conflicts has xStateActor or yStateActor participated in as a state party, and who are the opposing actors?",
            "Has xStateActor or yStateActor been engaged in any recognized armed conflicts in recent years?",
            "What are the legal classifications of conflicts involving xStateActor or yStateActor as a state actor?",
            "What IHL applies to the conflicts involving xStateActor and/or yStateActor as a state actor?",
            "How to classify xStateActor and/or yStateActor conflicts?",
            "What is the classification of conflicts involving the state actor xStateActor or yStateActor?",
            "Which IHL provisions apply to conflicts involving xStateActor or yStateActor?",
            "How does international humanitarian law classify conflicts involving xStateActor or yStateActor as a state actor?",
            "Which international treaties govern the conflicts involving the state actor xStateActor or yStateActor, i.e IHL law?",
            "What legal frameworks apply to conflicts involving xStateActor or yStateActor as a state actor?"
        ]
    },
     {
        "category": "4. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) Involving MULTIPLE State Actors WITH conflict classification FILTER",
        "questions": [
          "What IAC conflicts is the state actor xStateActor or yStateActor involved in?",
          "What NIAC conflicts is the state actor xStateActor or yStateActor involved in?",
          "What military occupations is the state actor xStateActor or yStateActor involved in?",
          "What IAC and NIAC conflicts is the state actor xStateActor or yStateActor involved in?",
          "What NIAC or IAC conflicts is xStateActor or yStateActor involved in?",
          "How many NIACs is xStateActor or yStateActor actively engaged in?",
          "Is the country xStateActor or yStateActor involved in any NIAC  conflict?",
          "Is xStateActor or yStateActor a party to any NIACs?",
          "Which non-international armed conflicts is xStateActor or yStateActor involved in as a state party?",
          "How many non-international armed conflicts is xStateActor or yStateActor involved in? What are their names?",
          "What non-international armed conflicts is xStateActor or yStateActor currently participating in as a state actor?",
          "How many NIACs is xStateActor or yStateActor involved in,  and what are their classifications?",
          "Has xStateActor or yStateActor been involved in any NIAC conflicts?",
          "Which NIACs has xStateActor or yStateActor participated in as a state party, and who are the opposing actors?",
          "Has xStateActor or yStateActor been engaged in any recognized NIACs conflicts  in recent years?",
          "What are the legal classifications of NIAC conflicts involving xStateActor or yStateActor as a state actor?",
          "What IHL applies to the NIACs involving xStateActor or yStateActor as a state actor?",
          "Which IHL provisions apply to NIACs involving xStateActor or yStateActor?",
          "How does international humanitarian law classify NIACs involving xStateActor or yStateActor as a state actor?",
          "Which international treaties govern the NIACs involving the state actor xStateActor or yStateActor, i.e IHL law?",
          "What legal frameworks apply to NIACS involving xStateActor or yStateActor as a state actor?"
        ]
      },
      {
        "category": "5. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) Involving MULTIPLE State Actors for COMPARING multiple state actors",
        "questions": [
            "Are there more conflicts involving xStateActor or yStateActor as state actors?",
            "Has xStateActor or yStateActor been involved in more armed conflicts?",
            "Is xStateActor or yStateActor involved in more armed conflicts?",
            "Do the conflicts involving xStateActor outnumber those involving yStateActor?",
            "Are there more conflicts involving xStateActor or yStateActor as a party to the conflict?",
            "How does the number of conflicts involving xStateActor compare to those involving yStateActor?",
            "Have more armed conflicts involved xStateActor or state actor yStateActor since 2014?",
            "Which state has been involved in more NIACs — xStateActor or yStateActor?",
            "Has state actor xStateActor or yStateActor engaged in more internationally recognized armed conflicts?",
            "Are there more conflicts involving xStateActor or yStateActor?",
            "Which state actor has been involved in more cross-border military operations— xStateActor or is it yStateActor?",
            "Have more conflicts involved xStateActor or yStateActor in the past three decades?",
            "Which state actor has participated in more military occupations— xStateActor or yStateActor?",
            "Do conflicts involving xStateActor outnumber those involving yStateActor?",
            "How does the number of conflicts involving xStateActor compare to those involving yStateActor?"        
        ]
    },
     {
        "category": "8. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a MULTIPLE CountrIES",
        "questions": [
          "What conflicts are taking place in xStateActor or yStateActor?",
          "How many conflicts are taking place in xStateActor or yStateActor?",
          "Are there any conflicts taking place in xStateActor or yStateActor?",
          "Which conflicts are taking place in xStateActor or yStateActor?",
          "What is the IHL that applies to the conflicts taking place in xStateActor or yStateActor?",
          "What are the classifications of the conflicts taking place in xStateActor or yStateActor?",
          "What is the legal framework involving the conflicts taking place in xStateActor or yStateActor?"
        ]
      },

      {
        "category": "9. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in MULTIPLE COUNTRIES WITH conflict classification FILTER",
        "questions": [
          "What IAC conflicts are taking place in xStateActor or yStateActor?",
          "What NIAC conflicts are taking place in xStateActor or yStateActor?",
          "What military occupations are taking place in xStateActor or yStateActor?",
          "What IAC and NIAC conflicts are taking place in xStateActor or yStateActor?",
          "How many NIACs are taking place in xStateActor or yStateActor?",
          "Which non-international armed conflicts are taking place in xStateActor or yStateActor?",
          "How many non-international armed conflicts are taking place in xStateActor or yStateActor? What are their names?",
          "Which IACs are taking place in xStateActor or yStateActor, and who are the opposing actors?",
          "What are the legal classifications of NIAC conflicts taking place in xStateActor or yStateActor?",
          "What IHL applies to the IACs that are taking place in xStateActor or in yStateActor?",
          "Which IHL provisions apply to IACs inside the countries: xStateActor and yStateActor?",
          "How does international humanitarian law classify  conflicts taking place in xStateActor or yStateActor?",
          "What legal frameworks apply to IACS taking place in xStateActor or yStateActor?"
        ]
      },
      {
        "category": "10. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in MULTIPLE Countries for COMPARING multiple countries",
        "questions": [
            "Are there more conflicts taking place in xStateActor or yStateActor?",
            "Do the conflicts taking place in xStateActor outnumber those taking place in yStateActor?",
            "Are there more conflicts taking place in xStateActor or yStateActor?",
            "How does the number of conflicts taking place in xStateActor compare to those taking place in yStateActor?",
            "Have more conflicts taken place geographically in xStateActor or yStateActor?",
            "Which country has more NIACs taking place —  xStateActor or yStateActor?",
            "Are there more conflicts taking place in xStateActor or yStateActor?",
            "Have more conflicts taken place in xStateActor or yStateActor in the past three decades?",
            "Do conflicts taking place in xStateActor outnumber those taking place in yStateActor?",
            "How does the number of conflicts taking place in xStateActor compare to those in yStateActor?"        
        ]
    },
]

# Define your list of questions with a placeholder for each region.
questions_for_each_region = [
  {
      "category": "11. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single GEOREGION",
        "questions": [
          "What conflicts are taking place in xGeoRegion?",
          "What IHL applies to the conflicts taking place in xGeoRegion region?"
        ]
    }
]


# Define your list of questions with a placeholder for a random region.
questions_for_random_region = [
  {
      "category": "11. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single GEOREGION",
        "questions": [
          "How many conflicts are taking place in xGeoRegion?",
          "Are there any conflicts taking place in xGeoRegion?",
          "Which conflicts are taking place in xGeoRegion?",
          "What are the classifications of the conflicts taking place in xGeoRegion?",
          "What is the legal framework involving the conflicts taking place in xGeoRegion?"
        ]
    },    
      {
        "category": "12. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single GEOREGION WITH conflict classification FILTER",
        "questions": [
          "What IAC conflicts are taking place in xGeoRegion?",
          "What NIAC conflicts are taking place in xGeoRegion?",
          "What military occupations are taking place in xGeoRegion?",
          "What IAC and NIAC conflicts are taking place in xGeoRegion?",
          "How many NIACs are taking place in xGeoRegion?",
          "Which non-international armed conflicts are taking place in xGeoRegion?",
          "How many non-international armed conflicts are taking place in xGeoRegion? What are their names?",
          "Which IACs are taking place in xGeoRegion, and who are the opposing actors?",
          "What are the legal classifications of NIAC conflicts taking place in xGeoRegion?",
          "What IHL applies to the IACs taking place in xGeoRegion?",
          "Which IHL provisions apply to IACs inside xGeoRegion?",
          "How does international humanitarian law classify conflicts in xGeoRegion?",
          "Which international treaties govern the NIACs taking place in xGeoRegion, i.e IHL law?",
          "What legal frameworks apply to NIACS taking place in xGeoRegion?"
        ]
      }
]



# Define your list of questions with placeholders for 2 random regions.
questions_for_random_two_regions = [
    {
        "category": "13. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a MULTIPLE REGIONS",
        "questions": [
          "What conflicts are taking place in xGeoRegion or yGeoRegion?",
          "How many conflicts are taking place in xGeoRegion or yGeoRegion?",
          "Are there any conflicts taking place in xGeoRegion or yGeoRegion?",
          "Which conflicts are taking place in xGeoRegion or yGeoRegion?",
          "What is the IHL that applies to the conflicts taking place in xGeoRegion or yGeoRegion?",
          "What are the classifications of the conflicts taking place in xGeoRegion or yGeoRegion?",
          "What is the legal framework involving the conflicts taking place in xGeoRegion or yGeoRegion?"
        ]
      },

      {
        "category": "14. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in MULTIPLE GEOREGIONS WITH conflict classification FILTER",
        "questions": [
          "What IAC conflicts are taking place in xGeoRegion or yGeoRegion?",
          "What NIAC conflicts are taking place in xGeoRegion or yGeoRegion?",
          "What military occupations are taking place in xGeoRegion or yGeoRegion?",
          "What IAC and NIAC conflicts are taking place in xGeoRegion or yGeoRegion?",
          "How many NIACs are taking place in xGeoRegion or yGeoRegion?",
          "Which non-international armed conflicts are taking place in xGeoRegion or yGeoRegion?",
          "How many non-international armed conflicts are taking place in xGeoRegion or yGeoRegion? What are their names?",
          "Which IACs are taking place in xGeoRegion or yGeoRegion, and who are the opposing actors?",
          "What are the legal classifications of NIAC conflicts taking place in xGeoRegion or yGeoRegion?",
          "What IHL applies to the IACs taking place in xGeoRegion or yGeoRegion?",
          "Which IHL provisions apply to IACs inside xGeoRegion or yGeoRegion?",
          "How does international humanitarian law classify conflicts in xGeoRegion or yGeoRegion?",
          "Which international treaties govern the NIACs taking place in xGeoRegion and yGeoRegion regions, i.e IHL law?",
          "What legal frameworks apply to NIACS taking place in xGeoRegion or yGeoRegion regions?"
        ]
      },
      {
        "category": "15. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in MULTIPLE GEOREGIONs for COMPARING multiple GEOREGIONs",
        "questions": [
            "Are there more conflicts taking place in xGeoRegion or yGeoRegion?",
            "Do the conflicts taking place in xGeoRegion outnumber those taking place in yGeoRegion?",
            "Are there more conflicts taking place in xGeoRegion or yGeoRegion?",
            "How does the number of conflicts taking place in xGeoRegion compare to those taking place in yGeoRegion?",
            "Have more conflicts taken place geographically in xGeoRegion or yGeoRegion?",
            "Which region has more NIACs taking place — xGeoRegion or yGeoRegion?",
            "Are there more conflicts taking place in xGeoRegion or yGeoRegion?",
            "Do conflicts taking place in xGeoRegion region outnumber those taking place in yGeoRegion?",
            "How does the number of conflicts taking place in  xGeoRegion region compare to those in yGeoRegion region?"        
        ]
    },
]

# Define your list of questions with a placeholder for each special region.
questions_for_each_special_region = [
    {
      "category": "16. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single SPECIAL REGION and by TYPE and several special regions (COMBO)",
        "questions": [
          "What conflicts are taking place in the xSpecialRegion?",
          "What IHL applies to the NIACS taking place in xSpecialRegion?",
        ]
    },  
]


# Define your list of questions with a placeholder for a random region.
questions_for_random_special_region = [
{
      "category": "16. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflict(s) TAKING PLACE in a single SPECIAL REGION and by TYPE and several special regions (COMBO)",
        "questions": [
          "What NIAC conflicts are taking place in the xSpecialRegion?",
          "How many military occupations are taking place in xSpecialRegion?",
          "Are there any conflicts taking place in xSpecialRegion?",
          "Which conflicts are taking place in xSpecialRegion?",
          "What are the classifications of the NIAC and IAC conflicts taking place in xSpecialRegion?",
          "What is the legal framework involving the conflicts taking place in xSpecialRegion?",
        ]
    },  
]

# Define your list of questions with a placeholder for each organization.
questions_for_each_organization = [
     {
      "category": "17. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflicts Involving International or Regional Political Organizations",
"questions": [
             "What conflicts involve state actors from the xOrganization organization?",
             "What conflicts are taking place in countries from the xOrganization organization?",
        ]
    }, 
]


# Define your list of questions with a placeholder for a random organization.
questions_for_random_organization = [
   {
      "category": "17. Conflict Data (name, classification, overview, applicable IHL, parties) for Conflicts Involving International or Regional Political Organizations",
"questions": [
             "How many conflicts involve xOrganization member states?",
             "What conflicts are taking place in countries from the xOrganization organization?",
             "What conflicts are xOrganization countries currently involved in?",
            "What conflicts involve xOrganization as state actors?",
            "Which conflicts have involved members of the xOrganization?",
            "Which conflicts have involved members of the xOrganization?",
            "Can you give me breakdown of xOrganization involvement in conflict?",
            "What conflicts involve xOrganization?",
            "How many active conflicts currently involve xOrganization member states?",
                "How many non-international armed conflicts involve xOrganization member states?",
                "How many non-international armed conflicts are taking place in xOrganization member countries?",
                "What armed conflicts are taking place in xOrganization member countries?",
                "How many armed conflicts involve xOrganization organization?"
        ]
    }, 
      {
        "category": "20. Ranking most /least global country conflict involvement across organization",
        "questions": [
            "Which xOrganization state actors / member countries have been party to the fewest conflicts?",
            "Which xOrganization state actors / member countries have been party to the most conflicts?",
            "Which xOrganization state members have been party to the most conflicts?",
            "Which xOrganization state actors / member countries have been party to the most conflicts?",
            "Which xOrganization state actors have been involved in the highest number of conflicts?",
            "Which xOrganization state actors / members have been involved in the least number of conflicts?",
            "Which xOrganization state actors have been involved in the highest number of non-international armed conflicts (NIACs)?",
            "Which xOrganization organization state actors have been directly involved in military occupations?",
            "Which xOrganization organization member state actors have been engaged in military occupations or IACs?"
        ]
    }   
]



# Define your list of questions with a placeholder for a random non state actor.
questions_for_random_NSA = [
    {
      "category": "18. Conflict lookup by non-state actor",
      "questions": [
        "how many NIAC conflicts involve xNSA?",
        "How many conflicts has xNSA been involved in, and who are the opposing parties?",
        "In which countries is xNSA currently active, and what are the applicable IHL frameworks?",
        "Which ongoing conflicts involve xNSA ?",
        "In which countries is xNSA currently active, and what are the applicable IHL frameworks?",
        "What are the main conflicts linked to xNSA, and how have they evolved?",
        "Which ongoing conflicts involve xNSA?",
        "What conflicts involve xNSA, and what are their classifications?",
        "Where has the xNSA been involved in NIACs?",
        "What is the involvement of xNSA in conflicts?",
        "Which conflicts have seen the participation of xNSA, and how has their role changed over time?",
        "What conflicts involve xNSA, and how have they interacted with state forces?",
        "Which conflicts have involved xNSA?",
        "How has xNSA been involved in conflicts, and what are the classifications of these conflicts?",
        "Which conflicts have seen significant involvement from xNSA?",
        "Are there any ongoing conflicts involving xNSA?",
        "Which conflicts have involved xNSA?",
        "What conflicts have included non-state actors like xNSA?",
        "Are there conflicts where xNSA were considered a significant armed actor?",
        "Which conflicts have involved xNSA?"
      ]
    },
]

# Define your list of questions with a placeholder for a random non state actor.
questions_for_global_manual_inclusion = [
 {
      "category": "19. Ranking most / least global country conflict involvement across world",
      "questions": [
        "Which state actors are involved in the most conflicts in the world?",
        "Which state actors are party to the most conflicts in the world?",
        "Which state actors are involved in the least conflicts in the world?",
        "Which state actors are party to the least conflicts in the world?",
        "Which countries are the most conflicts taking place in the world?",
        "Where are most conflicts taking place in the world?",
        "Which countries are the least conflicts taking place in the world?",
        "Where are the least amount of conflicts taking place in the world?",
        "Where are the fewest conflicts taking place in the world?",
        "Which countries have the fewest conflicts?",
        "Which state actors are involved in the most IACs in the world?",
        "Where are most IACs taking place in the world?",
  "Which five state actors have been involved in the highest number of armed conflicts?",
  "Which state actors are involved in the most military occupations?",
  "Which state actors are involved in the highest number of international armed conflicts (IACs)?",
  "Which state actors are involved in the highest number of non-international armed conflicts (NIACs)?",
  "Which countries have the highest number of international armed conflicts (IACs) taking place?",
  "Which countries have the highest number of non-international armed conflicts (NIACs) taking place?",

      ]
  },
]


nonStateActors = ["Abu Sayyaf Group", "African Union Mission in Somalia (AMISOM)", "Ahrar al-Sham", "Al-Qaeda in the Arabian Peninsula", "Al-Shabaab", "Allied Democratic Forces (ADF)", "Anglophone separatist groups", "Ansaroul Islam", "Anti-Balaka armed group", "Arakan Army (AA)", "Arakan Rohingya Salvation Army (ARSA)", "Bangsamoro Islamic Freedom Fighters (BIFF)", "Boko Haram", "CODECO", "Central African Liberators for Justice Movement (MLCJ)", "Central African Patriotic Movement (MPC)", "Communist Party of India - Maoist (Naxalites)", "Democratic Forces for the Liberation of Rwanda (FDLR)", "Derna Protection Force (DPF)", "Group for the Support of Islam and Muslims (JNIM)", "Hamas", "Hay'at Tahrir al-Sham", "Hezbollah", "Houthi", "IS-K", "ISWAP", "Islamic State group", "Islamic State in Somalia (ISS)", "Islamic State in West Africa Province (ISWAP)", "Islamic State in the Greater Sahara (ISGS)", "Jama'at Nusrat al-Islam wal-Muslimin (JNIM)", "Jamaat-ul-Ahrar", "Kurdistan Workers' Party (PKK)", "Lashkar-e-Jhangvi", "Libyan National Army", "M23", "MFDC- Front Sud", "Mai-Mai Yakutumba", "Maute Group", "Moro Islamic Liberation Front (MILF)", "Moro National Liberation Front (MNLF)", "Myanmar National Democratic Alliance Army (MNDAA)", "National Liberation Army (ELN)", "National Resistance Front (NRF)", "New People's Army (NPA)", "Oromo Liberation Army (OLA)", "Palestinian Islamic Jihad", "Polisario Front", "Popular Front for the Renaissance in the Central African Republic (FPRC)", "Rapid Support Forces (RSF)", "Return, Reclamation and Rehabilitation (3R)", "Russian-backed militias", "Southern Transitional Council (STC)", "Syrian Democratic Forces (including YPG)", "Séléka/ Ex-Séléka coalition group", "Ta'ang National Liberation Army (TNLA)", "Tehrik-i-Taliban (TTP)", "The Baloch Liberation Army", "The Barisan Revolusi Nasional (BRN)", "The Benghazi Revolutionaries Shura Council (BRSC)", "The Haqqani network", "The Islamic State group's Khorasan province branch (IS-KP)", "The National Salvation Front (NAS)", "The Sudan Liberation Movement/Army-Abdel Wahid (SLM/A-AW)", "The Sudan People's Liberation Movement/Army-in-Opposition (SPLM/A-IO)", "The Sudan People's Liberation Movement/Army - North Agar (SPLM-North Agar)", "The Sudan People's Liberation Movement/Army North Hilu (SPLM/AN Hilu)", "The Syrian National Army (SNA), former Free Syrian Army (FSA)", "The former Bloque Oriental (Eastern Bloc) of the Fuerzas Armadas Revolucionarias de Colombia Ejército del Pueblo (Revolutionary Armed Forces of Colombia - People's Army) (FARC-EP)", "Tigray People's Liberation Front (TPLF)", "Ukrainian separatist groups", "Union for Peace in the Central African Republic (UPC)", "United Nations Multidimensional Integrated Mission (MINUSCA)", "Wilayat Sinai (Sinai Province)", "Multinational Joint Task Force (MNJTF)"]



# Define list of regions
regions = [
    "Africa",
    "Northern Africa",
    "Sub-Saharan Africa",
    "Eastern Africa",
    "Middle Africa",
    "Southern Africa",
    "Western Africa",
    "Americas",
    "Northern America",
    "Caribbean",
    "Central America",
    "Latin America and the Caribbean",
    "South America",
    "Antarctica",
    "Asia",
    "Central Asia",
    "Eastern Asia",
    "South-Eastern Asia",
    "Southern Asia",
    "Western Asia",
    "Europe",
    "Eastern Europe",
    "Northern Europe",
    "Southern Europe",
    "Western Europe",
    "Oceania"
]

special_regions = [
    "Great Lakes Region",
    "Horn of Africa Region",
    "Sahel Region",
    "Baltic States",
    "Arctic Region",
    "Levant Region",
    "Caucasus Region",
    "Balkan Region"
]

organizations = [
     "European Union", "African Union", "G7", "BRICS", "NATO", "ASEAN"
]

# Define your list of countries (state actors).
countries = [
    "Afghanistan", "Albania", "Algeria", "American Samoa", "Andorra", "Angola",
    "Anguilla", "Antarctica", "Antigua and Barbuda", "Argentina", "Armenia", "Aruba",
    "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados",
    "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan",
    "Bolivia", 
    "Bosnia and Herzegovina", "Botswana", "Bouvet Island", "Brazil",
    "British Indian Ocean Territory", "British Virgin Islands", "Brunei Darussalam",
    "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada",
    "Cayman Islands", "Central African Republic", "Chad", "Chile", "China",
    "Colombia", "Comoros", "Congo",
    "Cook Islands", "Costa Rica", "Côte d'Ivoire", "Croatia", "Cuba", "Curaçao", "Cyprus",
    "Czechia", "Democratic People's Republic of Korea", "Democratic Republic of the Congo",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt",
    "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
    "Falkland Islands (Malvinas)", "Fiji", "Finland", "France", "French Guiana",
    "French Polynesia", "French Southern Territories", "Gabon", "Gambia", "Georgia", "Germany",
    "Ghana", "Gibraltar", "Greece", "Greenland", "Grenada", "Guadeloupe", "Guam", "Guatemala",
    "Guernsey", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Heard Island and McDonald Islands",
    "Holy See", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran",
    "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jersey", "Jordan",
    "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Lao People's Democratic Republic",
    "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania",
    "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta",
    "Marshall Islands", "Martinique", "Mauritania", "Mauritius", "Mayotte", "Mexico",
    "Micronesia (Federated States of)", "Monaco", "Mongolia", "Montenegro", "Montserrat",
    "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal",
    "Netherlands", "New Caledonia", "New Zealand", "Nicaragua", "Niger",
    "Nigeria", "Niue", "Norfolk Island", "North Macedonia", "Northern Mariana Islands",
    "Norway", "Oman", "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay",
    "Peru", "Philippines", "Pitcairn", "Poland", "Portugal", "Puerto Rico", "Qatar",
    "Republic of Korea", "Republic of Moldova", "Réunion", "Romania", "Russian Federation",
    "Rwanda", "Saint Barthélemy", "Saint Helena", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Martin (French Part)", "Saint Pierre and Miquelon", "Saint Vincent and the Grenadines",
    "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
    "Seychelles", "Sierra Leone", "Singapore", "Sint Maarten (Dutch part)", "Slovakia",
    "Slovenia", "Solomon Islands", "Somalia", "South Africa",
    "South Georgia and the South Sandwich Islands", "South Sudan", "Spain", "Sri Lanka",
    "State of Palestine", "Sudan", "Suriname", "Svalbard and Jan Mayen Islands", "Sweden",
    "Switzerland", "Syrian Arab Republic", "Tajikistan", "Thailand", "Timor-Leste", "Togo",
    "Tokelau", "Tonga", "Trinidad and Tobago", "Tunisia", "Türkiye/Turkey", "Turkmenistan",
    "Turks and Caicos Islands", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates",
    "United Kingdom of Great Britain and Northern Ireland", "United Republic of Tanzania",
    "United States of America", "United States Virgin Islands",
    "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela", "Viet Nam",
    "Wallis and Futuna Islands", "Western Sahara", "Yemen", "Zambia", "Zimbabwe"
]

# Prepare a list to hold the generated questions.
output_questions = []

# Generate questions for each country.
for entry in questions_for_each_country:
    category = entry.get("category", "")
    for country in countries:
        for question in entry.get("questions", []):
            filled_question = question.replace("xStateActor", country).strip()
            output_questions.append({
                "category": category,
                "country": country,
                "question": filled_question
            })

# Generate questions for a random country per question, repeating 3 times for each question.
for entry in questions_for_random_country:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(3):  # Repeat 3 times for each question.
            random_country = random.choice(countries)
            filled_question = question.replace("xStateActor", random_country).strip()
            output_questions.append({
                "category": category,
                "country": random_country,
                "question": filled_question
            })

# Generate questions for each region.
for entry in questions_for_each_region:
    category = entry.get("category", "")
    for region in regions:
        for question in entry.get("questions", []):
            filled_question = question.replace("xGeoRegion", region).strip()
            output_questions.append({
                "category": category,
                "geoRegion": region,
                "question": filled_question
            })

# Generate questions for a random region per question, repeating 2 times for each question.
for entry in questions_for_random_region:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(2):  # Repeat 2 times for each question.
            random_region = random.choice(regions)
            filled_question = question.replace("xGeoRegion", random_region).strip()
            output_questions.append({
                "category": category,
                "geoRegion": random_region,
                "question": filled_question
            })

# Generate questions for each special region.
for entry in questions_for_each_special_region:
    category = entry.get("category", "")
    for region in special_regions:
        for question in entry.get("questions", []):
            filled_question = question.replace("xSpecialRegion", region).strip()
            output_questions.append({
                "category": category,
                "geoRegion": region,
                "question": filled_question
            })

# Generate questions for a random special region per question, repeating 2 times for each question.
for entry in questions_for_random_special_region:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(2):  # Repeat 2 times for each question.
            random_region = random.choice(special_regions)
            filled_question = question.replace("xSpecialRegion", random_region).strip()
            output_questions.append({
                "category": category,
                "geoRegion": random_region,
                "question": filled_question
            })

# Generate questions for two random countries per question, repeating 3 times for each question.
for entry in questions_for_random_two_countries:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(3):  # Repeat 3 times for each question.
            # Pick two distinct random countries.
            country_x, country_y = random.sample(countries, 2)
            filled_question = question.replace("xStateActor", country_x).replace("yStateActor", country_y).strip()
            output_questions.append({
                "category": category,
                "countries": [country_x, country_y],
                "question": filled_question
            })


# Generate questions for two random regions per question, repeating 2 times for each question.
for entry in questions_for_random_two_regions:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(2):  # Repeat 3 times for each question.
            # Pick two distinct random countries.
            region_x, region_y = random.sample(regions, 2)
            filled_question = question.replace("xGeoRegion", region_x).replace("yGeoRegion", region_y).strip()
            output_questions.append({
                "category": category,
                "GeoRegions": [region_x, region_y],
                "question": filled_question
            })

# Generate questions for each special region.
for entry in questions_for_each_organization:
    category = entry.get("category", "")
    for organization in organizations:
        for question in entry.get("questions", []):
            filled_question = question.replace("xOrganization", organization).strip()
            output_questions.append({
                "category": category,
                "xOrganization": organization,
                "question": filled_question
            })

# Generate questions for a random organization per question, repeating 2 times for each question.
for entry in questions_for_random_organization:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(2):  # Repeat 2 times for each question.
            random_organization = random.choice(organizations)
            filled_question = question.replace("xOrganization", random_organization).strip()
            output_questions.append({
                "category": category,
                "xOrganization": random_organization,
                "question": filled_question
            })

# Generate questions for a random non state actor per question, repeating 4 times for each question.
for entry in questions_for_random_NSA:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
        for _ in range(4):  # Repeat 4 times for each question.
            random_NSA = random.choice(nonStateActors)
            filled_question = question.replace("xNSA", random_NSA).strip()
            output_questions.append({
                "category": category,
                "NSA": random_NSA,
                "question": filled_question
            })

# Add manual questions for world related questions
for entry in questions_for_global_manual_inclusion:
    category = entry.get("category", "")
    for question in entry.get("questions", []):
            output_questions.append({
                "category": category,
                "WORLD": "WORLD",
                "question": question
            })

# Write the results to a JSON file in UTF-8 encoding.
with open("output_questions.json", "w", encoding="utf8") as outfile:
    json.dump(output_questions, outfile, indent=2, ensure_ascii=False)

# Print the total number of generated questions.
print(f"JSON file 'output_questions.json' has been generated with {len(output_questions)} questions.")
