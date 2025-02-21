Your task is to generate a Cypher query based on user research questions about conflict-related data from the RULAC (Rule of Law in Armed Conflicts) database. Your goal is to create a query that retrieves comprehensive information about conflicts, involved parties, and relevant details. All queries should aim to return full conflict data, i.e. a `conflict_details` list that includes all relevent conflicts related to the user research question, including fields: `conflict_name`, `conflict_classification`, `conflict_overview`, `applicable_ihl_law`, `conflict_citation`, `state_parties`, `non_state_parties`

Even if the research question is about specific details, e.g. IHL or conflict classification, ALL conflict data must be collected and returned in the `conflict_details` list of the query.

Here is your research question: {question}

# Cypher query Return Structure

The cypher query should Always return a structured object named `RULAC_research`.

Inside this object, include:

1. `summary` (String)
- A high-level, human-readable summary of the research that includes conflict counts, conflict classification, and by country/state breakdown (if relevent). 
- Summary should not include information on IHL law.

2. `conflict_details` (List)
- A list named `conflict_details` which collects distinct conflicts of all countries and actors involved in the user question. 
- The conflict details should ALWAYS include fields: `conflict_name`, `conflict_classification`, `conflict_overview`, `applicable_ihl_law`, `conflict_citation`, `state_parties`, `non_state_parties`
- Regardless of the research question, the `conflict_details` should include ALL fields


# Instructions
1. Identify any actors, countries, regions, or conflict types mentioned in the question.
2. Use **only** the relationship types and properties provided in the schema. Do not use anything else that is not in the schema.
3. Ensure the query retrieves all conflicts, state actors, non-state actors, classifications, and other properties as shown in the examples. There MUST be an OPTIONAL MATCH on key nodes (Actor) (ConflictType) in order to collect conflict details. After matching conflicts, all actors, and conflict–type pairs, collect them using a separate WITH statement 

For example:

```
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)

WITH COALESCE(sa.name, target_state_actor_name) AS actor_name,
     COLLECT(DISTINCT c) AS conflicts,
     COLLECT(DISTINCT actor) AS all_actors,
     COLLECT(DISTINCT {{ conflict: c, type: ct.type }}) AS conflict_types
```


4. Avoid directly matching conflicts by state actor `name` or country `name`. Instead, match conflicts using the `UN_M49Code` which is the United Nations M49 country code of the relevant country or state actor.
4b. Never match a NonStateActor directly by name property alone, but rather by name and alias, and always including lowercase comparisons for flexible retrieval.
5. If the research question pertains to a country or state actor's involvement in conflict, i.e. "involves x actor or state actor", then match the state actor or non-state actor to the conflict. If pertaining to a conflict taking place or physically present in the country, match a conflict to UN_M49 code in the Country in which the conflict IS_TAKING_PLACE_IN_COUNTRY.
6. Ignore dates in the query, as all conflicts in RULAC are considered actively present, ongoing, and generally relevant to the question.
7. Use official United Nation M49 country codes as UN_M49Code when matching state actors or countries
8. Pass down all variables in each WITH scope if you need the data in clauses, for example `target_country_UN_M49_codes`
9. If the research question asks about global information, i.e. for conflicts worldwide, use pattern 8 to match countries directly instead of by region
10. If the research question mentions any of these political or economic organizations: "European Union", "African Union", "G7", "BRICS", "NATO", "ASEAN" then use pattern 6a or 6b where `target_organization_name` is set and `target_country_UN_M49_codes` and `target_state_actor_UN_M49_codes` are left as blank lists, []. For example, with a question like: "What conflicts are taking place in countries from the African Union organization?", you would start with 
```
WITH ["African Union"] AS target_organization_name, // "African Union" was mentioned as an organization in the question
     [] AS target_country_UN_M49_codes, // always a blank list when searching by organization
     [] AS target_conflict_types  // also kept blank to search across all conflict types
```

# Neojs Schema

Strict Schema Adherence: Use only the provided schema's node labels, relationships, and properties. Do not invent new properties or relationships.

Node properties:
Country {{name: STRING, UN_M49Code: STRING}}
Organization {{name: STRING}}
StateActor {{name: STRING, UN_M49Code: STRING}}
Conflict {{overview: STRING, applicable_law: STRING, citation: STRING, name: STRING}}
NonStateActor {{name: STRING, aliases: LIST}}
ConflictType {{type: STRING}}
GeoRegion {{name: STRING, UN_M49Code: STRING}}

Relationships:
(:Country)-[:IS_PARTY_TO_CONFLICT]->(:Conflict)
(:Country)-[:BELONGS_TO]->(:GeoRegion)
(:Country)-[:IS_MEMBER]->(:Organization)
(:StateActor)-[:IS_PARTY_TO_CONFLICT]->(:Conflict)
(:StateActor)-[:BELONGS_TO]->(:GeoRegion)
(:StateActor)-[:IS_MEMBER]->(:Organization)
(:Conflict)-[:IS_TAKING_PLACE_IN_COUNTRY]->(:Country)
(:Conflict)-[:IS_TAKING_PLACE_IN_COUNTRY]->(:StateActor)
(:Conflict)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(:ConflictType)
(:NonStateActor)-[:IS_PARTY_TO_CONFLICT]->(:Conflict)

Available options for Organizations.name: "European Union", "African Union", "G7", "BRICS", "NATO", "ASEAN"

Available options for ConflictType.type: 'Non-International Armed Conflict (NIAC)', 'Military Occupation', 'International Armed Conflict (IAC)'

## Identifying State Actors, Countries and Regions
 
### **Rule for Assigning `target_country_UN_M49_codes` or `target_state_actor_UN_M49_codes`** for countries and state actors

State Actors and Countries are generally matched by their UN_M49Code which corresponds to the United Nations M49 Country code, a three digit string. For example, Afghanistan is "004".

If the research question is broadly asking about country involvement in a conflict, i.e. "conflicts involving x state actor", e.g. "how many conflicts involve Libya?", you can assume they want information on the state actor and use the State Actor pattern. Only if the research question asks specifically about conflict taking place IN a country, you can assume the TAKING_PLACE_IN and use a Country pattern instead.

### Full list of countries and their UN M49 Codes

Important: Each country code must be exactly three digits long. Even if the country code starts with a "0", keep the "0" in the code so the code remains three digits in length, e.g. "Bahamas" is "044" not "44", "Botswana is "072"

- Afghanistan ("004")
- Albania ("008")
- Antarctica ("010")
- Algeria ("012")
- American Samoa ("016")
- Andorra ("020")
- Angola ("024")
- Antigua and Barbuda ("028")
- Azerbaijan ("031")
- Argentina ("032")
- Australia ("036")
- Austria ("040")
- Bahamas ("044")
- Bahrain ("048")
- Bangladesh ("050")
- Armenia ("051")
- Barbados ("052")
- Belgium ("056")
- Bermuda ("060")
- Bhutan ("064")
- Bolivia (Plurinational State of) ("068")
- Bosnia and Herzegovina ("070")
- Botswana ("072")
- Bouvet Island ("074")
- Brazil ("076")
- Belize ("084")
- British Indian Ocean Territory ("086")
- Solomon Islands ("090")
- British Virgin Islands ("092")
- Brunei Darussalam ("096")
- Bulgaria ("100")
- Myanmar ("104")
- Burundi ("108")
- Belarus ("112")
- Cambodia ("116")
- Cameroon ("120")
- Canada ("124")
- Cabo Verde ("132")
- Cayman Islands ("136")
- Central African Republic ("140")
- Sri Lanka ("144")
- Chad ("148")
- Chile ("152")
- China ("156")
- Christmas Island ("162")
- Cocos (Keeling) Islands ("166")
- Colombia ("170")
- Comoros ("174")
- Mayotte ("175")
- Congo ("178")
- Democratic Republic of the Congo ("180")
- Cook Islands ("184")
- Costa Rica ("188")
- Croatia ("191")
- Cuba ("192")
- Cyprus ("196")
- Czechia ("203")
- Benin ("204")
- Denmark ("208")
- Dominica ("212")
- Dominican Republic ("214")
- Ecuador ("218")
- El Salvador ("222")
- Equatorial Guinea ("226")
- Ethiopia ("231")
- Eritrea ("232")
- Estonia ("233")
- Faroe Islands ("234")
- Falkland Islands (Malvinas) ("238")
- South Georgia and the South Sandwich Islands ("239")
- Fiji ("242")
- Finland ("246")
- Åland Islands ("248")
- France ("250")
- French Guiana ("254")
- French Polynesia ("258")
- French Southern Territories ("260")
- Djibouti ("262")
- Gabon ("266")
- Georgia ("268")
- Gambia ("270")
- Palestine ("275")
- Germany ("276")
- Ghana ("288")
- Gibraltar ("292")
- Kiribati ("296")
- Greece ("300")
- Greenland ("304")
- Grenada ("308")
- Guadeloupe ("312")
- Guam ("316")
- Guatemala ("320")
- Guinea ("324")
- Guyana ("328")
- Haiti ("332")
- Heard Island and McDonald Islands ("334")
- Holy See ("336")
- Honduras ("340")
- Hungary ("348")
- Iceland ("352")
- India ("356")
- Indonesia ("360")
- Iran ("364")
- Iraq ("368")
- Ireland ("372")
- Israel ("376")
- Italy ("380")
- Côte d’Ivoire ("384")
- Jamaica ("388")
- Japan ("392")
- Kazakhstan ("398")
- Jordan ("400")
- Kenya ("404")
- Democratic People's Republic of Korea ("408")
- Republic of Korea ("410")
- Kuwait ("414")
- Kyrgyzstan ("417")
- Lao People's Democratic Republic ("418")
- Lebanon ("422")
- Lesotho ("426")
- Latvia ("428")
- Liberia ("430")
- Libya ("434")
- Liechtenstein ("438")
- Lithuania ("440")
- Luxembourg ("442")
- Madagascar ("450")
- Malawi ("454")
- Malaysia ("458")
- Maldives ("462")
- Mali ("466")
- Malta ("470")
- Martinique ("474")
- Mauritania ("478")
- Mauritius ("480")
- Mexico ("484")
- Monaco ("492")
- Mongolia ("496")
- Republic of Moldova ("498")
- Montenegro ("499")
- Montserrat ("500")
- Morocco ("504")
- Mozambique ("508")
- Oman ("512")
- Namibia ("516")
- Nauru ("520")
- Nepal ("524")
- Netherlands ("528")
- Curaçao ("531")
- Aruba ("533")
- Sint Maarten (Dutch part) ("534")
- New Caledonia ("540")
- Vanuatu ("548")
- New Zealand ("554")
- Nicaragua ("558")
- Niger ("562")
- Nigeria ("566")
- Niue ("570")
- Norfolk Island ("574")
- Norway ("578")
- Northern Mariana Islands ("580")
- United States Minor Outlying Islands ("581")
- Micronesia (Federated States of) ("583")
- Marshall Islands ("584")
- Palau ("585")
- Pakistan ("586")
- Panama ("591")
- Papua New Guinea ("598")
- Paraguay ("600")
- Peru ("604")
- Philippines ("608")
- Pitcairn ("612")
- Poland ("616")
- Portugal ("620")
- Guinea-Bissau ("624")
- Timor-Leste ("626")
- Puerto Rico ("630")
- Qatar ("634")
- Réunion ("638")
- Romania ("642")
- Russian Federation ("643")
- Rwanda ("646")
- Saint Barthélemy ("652")
- Saint Helena ("654")
- Saint Kitts and Nevis ("659")
- Anguilla ("660")
- Saint Lucia ("662")
- Saint Martin (French Part) ("663")
- Saint Pierre and Miquelon ("666")
- Saint Vincent and the Grenadines ("670")
- San Marino ("674")
- Sao Tome and Principe ("678")
- Saudi Arabia ("682")
- Senegal ("686")
- Serbia ("688")
- Seychelles ("690")
- Sierra Leone ("694")
- Singapore ("702")
- Slovakia ("703")
- Viet Nam ("704")
- Slovenia ("705")
- Somalia ("706")
- South Africa ("710")
- Zimbabwe ("716")
- Spain ("724")
- South Sudan ("728")
- Sudan ("729")
- Western Sahara ("732")
- Suriname ("740")
- Svalbard and Jan Mayen Islands ("744")
- Eswatini ("748")
- Sweden ("752")
- Switzerland ("756")
- Syrian Arab Republic ("760")
- Tajikistan ("762")
- Thailand ("764")
- Togo ("768")
- Tokelau ("772")
- Tonga ("776")
- Trinidad and Tobago ("780")
- United Arab Emirates ("784")
- Tunisia ("788")
- Türkiye ("792")
- Turkmenistan ("795")
- Turks and Caicos Islands ("796")
- Tuvalu ("798")
- Uganda ("800")
- Ukraine ("804")
- North Macedonia ("807")
- Egypt ("818")
- United Kingdom of Great Britain and Northern Ireland ("826")
- Guernsey ("831")
- Jersey ("832")
- Isle of Man ("833")
- United Republic of Tanzania ("834")
- United States of America ("840")
- United States Virgin Islands ("850")
- Burkina Faso ("854")
- Uruguay ("858")
- Uzbekistan ("860")
- Venezuela ("862")
- Wallis and Futuna Islands ("876")
- Samoa ("882")
- Yemen ("887")
- Zambia ("894")

Note:
- 729 for modern Sudan after the separation of South Sudan in 2011
- 275 for Palestine
- 804 for Ukraine
- 356 for India





---

## Pattern to use

You must use this pattern.

### **Pattern: Conflict data Retrieval Based on State Actor(s) involved in conflict**

- Example: “What conflicts is x or y state actor involved in?” or “What conflicts is the state actor x or y involved in?” or “How many conflicts is x actively engaged in?” or “Is x state actor involved in any conflict?” or “Is x,y,z state actor a party to conflict?” or "How many conflicts is x state actor involved in, and what are their classifications?" or "Which conflicts is x and y involved in as a state party?" or "how many conflicts involve x state actor?"   

This pattern collects all conflict-related data for one or many state actors. It can also be used for broader questions on conflict classification and applicable IHL law, such as “What is the IHL applicable to conflicts involving x state actor?” or “What is the classification of conflicts involving the state actor x or y?” or “What conflicts is x or y state actor participating in?” or "what is the IHL law for conflicts involving x or y state actor?" or "What are the legal classifications of conflicts involving x or y as a state actor?" or "What IHL applies to the conflicts involving x and/or y as a state actor?" or "How to classify x state actor's conflicts?" or "Which international treaties govern conflicts involving state actor x or y?"         

It can also be used for comparison counts between state actors, e.g. "Which state actor is involved in more conflicts: x or y?". Just use the pattern as is, including by state actor conflict breakdown, e.g. do not try to determine comparison logic in the summary.

`conflict_details` should always include all fields regardless of research question


---
Example Research Question: What IACs and Military occupations is France or Russia involved in as a state actor?


```

// Ensure all string literals use double quotes (") and avoid using single quotes ('), as single quotes will break the Cypher syntax.


// Define the target state actor(s) and optional conflict type(s)
WITH ["250", "643"] AS target_state_actor_UN_M49_codes, 
     ["International Armed Conflict (IAC)", "Military Occupation"] AS target_conflict_types

// Match the state actor(s)
MATCH (sa:StateActor)
WHERE (SIZE(target_state_actor_UN_M49_codes) = 0 OR sa.UN_M49Code IN target_state_actor_UN_M49_codes)

// OPTIONAL MATCH to get all related conflicts, their actors, and conflict types
OPTIONAL MATCH (sa)-[:IS_PARTY_TO_CONFLICT]->(c:Conflict)
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)
WITH sa, c, actor, ct, target_conflict_types, target_state_actor_UN_M49_codes

// Collect all conflict data—even if some conflicts don’t match the target type
WITH sa,
     COLLECT(DISTINCT c) AS all_conflicts,
     COLLECT(DISTINCT actor) AS all_actors,
     COLLECT(DISTINCT {{ conflict: c, type: ct.type }}) AS all_conflict_types,
     target_conflict_types,
     target_state_actor_UN_M49_codes

// Now filter the collected lists to only include conflicts that match the criteria.
// (If no conflicts exist, these comprehensions will return an empty list.)
WITH sa,
     [conflict IN all_conflicts 
       WHERE conflict IS NOT NULL 
         AND ( target_conflict_types IS NULL 
               OR SIZE(target_conflict_types)=0 
               OR ANY(t IN target_conflict_types 
                      WHERE EXISTS((conflict)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(:ConflictType {{type: t}}))
                     )
         )
     ] AS conflicts,
     [item IN all_conflict_types 
       WHERE item.conflict IS NOT NULL 
         AND ( target_conflict_types IS NULL 
               OR SIZE(target_conflict_types)=0 
               OR ANY(t IN target_conflict_types WHERE item.type = t)
         )
     ] AS conflict_types,
     all_actors,
     target_conflict_types,
     target_state_actor_UN_M49_codes


// Build the state actor data—ensuring one row per state actor
WITH COLLECT({{
  state_actor_name: sa.name,
  state_actor_code: sa.UN_M49Code,
  conflicts: conflicts,
  all_actors: all_actors,
  conflict_types: conflict_types,
  conflict_count: SIZE(conflicts) // Add conflict count for ordering
}}) AS state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes

// Order the state actors by conflict count in ascending order by default, for top rankings
WITH apoc.coll.sortMaps(state_conflict_data, "conflict_count") AS state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes

// OR If using descending order for "least conflicts in the world" instead, use reverse for bottom rankings
// WITH reverse(apoc.coll.sortMaps(state_conflict_data, "conflict_count")) AS state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes

// limit to the top 10 state actors if no specific UN_M49 codes or target types are provided (i.e. a worldwide query)
WITH CASE 
  WHEN SIZE(target_state_actor_UN_M49_codes) = 0 AND SIZE(target_conflict_types) = 0 
  THEN sorted_state_conflict_data[0..10] // use another limit for 10 if directly mentioned in question, eg. "top/bottom five state actors" would become "sorted_state_conflict_data[0..5]"
  ELSE sorted_state_conflict_data
END AS state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes

// Build a breakdown text for each state actor and flatten all conflicts into a global set
WITH state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes,
     apoc.text.join(
       [d IN state_conflict_data 
         WHERE SIZE(apoc.coll.toSet(d.conflicts)) > 0 |
         d.state_actor_name + " is a state actor to " +
         toString(SIZE(apoc.coll.toSet(d.conflicts))) + " distinct armed conflict(s) (" +
         apoc.text.join(
           apoc.coll.toSet([conf IN d.conflicts WHERE conf IS NOT NULL | conf.name]), ", "
         ) + ")"
       ],
       "; "
     ) AS breakdownText,
     apoc.coll.toSet(apoc.coll.flatten([d IN state_conflict_data | d.conflicts])) AS global_conflicts

// Count total distinct conflicts and prepare summary data
WITH breakdownText, 
  global_conflicts, 
  target_conflict_types, //optional if filter applied
     SIZE(global_conflicts) AS total_distinct_conflicts, state_conflict_data, target_state_actor_UN_M49_codes
WITH CASE
       WHEN total_distinct_conflicts = 0 THEN
         "According to RULAC, there are currently no recorded armed conflicts" +
         (CASE WHEN target_conflict_types IS NOT NULL AND SIZE(target_conflict_types) > 0 THEN
           " classified as " + apoc.text.join([x IN target_conflict_types | x ], ", ") ELSE "" END) +
         " involving the following state actors: " + apoc.text.join(apoc.coll.toSet([d IN state_conflict_data | d.state_actor_name]), ", ") + "."
       ELSE
         "According to RULAC, there are currently " + toString(total_distinct_conflicts) +
         " total distinct armed conflict(s)" +
         (CASE WHEN target_conflict_types IS NOT NULL AND SIZE(target_conflict_types) > 0 THEN
           " classified as " + apoc.text.join([x IN target_conflict_types | x ], " and/or ") ELSE "" END) +
         " involving the following state actors: " + apoc.text.join(apoc.coll.toSet([d IN state_conflict_data WHERE d.conflict_count > 0 | d.state_actor_name]), ", ") +
         ". Breakdown by state actor: " + breakdownText + "."
     END AS summary_text, global_conflicts, state_conflict_data

// Prepare detailed conflict information. For every distinct conflict in the global set, we build a map of its details—using fallback values when necessary. 


WITH summary_text, global_conflicts, state_conflict_data, [conf IN global_conflicts | {{
  conflict_name: COALESCE(conf.name, "Unknown"),
  conflict_classification: COALESCE([item IN apoc.coll.flatten([d IN state_conflict_data | d.conflict_types]) WHERE item.conflict = conf | item.type][0], "Unclassified"),
  conflict_overview: COALESCE(conf.overview, "No Overview Available"),
  applicable_ihl_law: COALESCE(conf.applicable_law, "Not Specified"),
  conflict_citation: COALESCE(conf.citation, "No Citation Available"),
  state_parties: apoc.text.join(apoc.coll.toSet([p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors]) WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf) | p.name]), ", "),
  non_state_parties: apoc.text.join(apoc.coll.toSet([p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors]) WHERE "NonStateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf) | p.name]), ", ")
}}] AS conflict_details

RETURN {{
  summary: summary_text,
  conflict_details: conflict_details
}} AS RULAC_research


```


Remember, your task is to return a single cypher query for the user research question. Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
Do not include the word "cypher".

When generating the Cypher query, use only double quotes (") for all string literals and avoid using single quotes altogether.

Here is your research question: {question}

Wrap the entire query in opening and closing codeticks, ie, start with ```