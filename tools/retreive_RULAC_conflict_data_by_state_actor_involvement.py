# retreive_RULAC_conflict_data_by_state_actor_involvement.py
from typing import List
from langchain_core.tools import tool
from rich.console import Console
from rich.panel import Panel
from langchain_neo4j import Neo4jGraph


@tool
async def retreive_RULAC_conflict_data_by_state_actor_involvement(
    query: str, 
    research_query: str,
    target_state_actor_UN_M49_codes: List,
    target_conflict_types: List,
    pipeSelf=None,
    event_emitter=None,
) -> str:
    """
    Retreives comprehensive conflict data from RULAC (Rule of Law in Armed Conflict) on armed conflicts (International Armed Conflicts (IAC), Non-International Armed Conflicts (NIAC), and Military Occupations) involving state actors. 
    
    Conflict data returned includes: conflict name, historical conflict overview, applicable international humanitarian law, conflict classification, and a list of state actors and non-state actors to the conflict. 

    This tool retreive all conflicts per xStateActor by default, but can also use an optional filter by conflict classification type. Note: There are only three valid conflict classifications, as defined by RULAC: "International Armed Conflict (IAC)", "Non-International Armed Conflict (NIAC)", "Military Occupation".


    ## Steps
    1. Identify the most relevent research_query from the user query
    2. Identify the state actor(s) to retreive conflict data
    3. Identify any conflict classification filters to apply, if requested. If there are no conflict classification filters to apply, return an empty [] for target_conflict_types


    ## Example Tool Call Parameters
    
    query: "What IAC and Military Occupation conflicts involve state actors France and Russia?"
    research_query: "Retreive RULAC conflict data involving France and Russia for conflicts classified as 'International Armed Conflict (IAC)' and 'Military Occupation'"
    target_state_actor_UN_M49_codes: ["250", "643"]
    target_conflict_types: ["International Armed Conflict (IAC)", "Military Occupation"]

    query: "What conflicts is USA a party to and what IHL law applies?"
    research_query: "Retreive RULAC conflict data involving United States of America"
    target_state_actor_UN_M49_codes: ["840"]
    target_conflict_types: []



### Full list of countries and their UN M49 Codes

Important: Each country code is three digits long. Even if the country code starts with a "0", keep the "0" in the code so the code remains three digits in length, e.g. "Bahamas" is "044" not "44", "Botswana is "072"

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
- Côte d'Ivoire ("384")
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

    



    :param query: The initial user research query to retreive conflict data. Must include enough context for retreival.
    :param research_query: General Retreival query
    :param target_state_actor_UN_M49_codes: List of UN_M49 codes for identified state actors in query
    :param target_conflict_types: List of conflict classification types to filter by in query
    


    :return: A JSON string with the answer
    """

    self = pipeSelf  # named diff to not conflict w reserved self keyword in initial parameters
    __event_emitter__ = event_emitter


    #Define and emit event
    eventMessageUI = "📚 Gathering data..."
    # Emit event for UI (user facing)
    if __event_emitter__:
        await __event_emitter__(
            {
                "type": "status",
                "data": {
                    "description": eventMessageUI,
                    "done": False,
                },
            }
        )
    # Emit event for logs (developer facing)
    panel = Panel.fit(eventMessageUI, style="black on yellow", border_style="yellow")       
    # Print nicely formatted box to console
    console.print(panel)




    # Use the pipeSelf object to get the Neo4j connection details.
    neo4j_url = self.neo4j_url

    # Debugging: Neo4j connection
    print(f"DEBUG: Connecting to Neo4j at {neo4j_url} with username {self.valves.neo4j_username}")

    try:
        # Connect to Neo4j using the provided credentials
        graph = Neo4jGraph(
            url=neo4j_url,
            username=self.valves.neo4j_username,
            password=self.valves.neo4j_password,
            enhanced_schema=False,
        )
    except Exception as conn_error:
        raise Exception(f"Error connecting to Neo4j: {conn_error}") from conn_error

    # Prepare the parameters for the query
    params = {
        "target_state_actor_UN_M49_codes": target_state_actor_UN_M49_codes,
        "target_conflict_types": target_conflict_types,
    }

    # Define the prewritten Cypher query. Note the use of $parameter_name for parameter substitution.
 
    # target_non_state_actor_name_and_aliases
 
    # Load tool-specific cypher template from GitHub
    TOOL_RULAC_StateActors_SYSTEM_PROMPT_URL = "https://raw.githubusercontent.com/andrewkess/beacon/main/prompts/indv_tool_prompts/tool_cypher_RULAC_conflict_by_StateActor.txt"
    cypher_query = load_template_from_github(TOOL_RULAC_StateActors_SYSTEM_PROMPT_URL)


    # DEBUGGING statement
    # Create a debug version of the query with parameters substituted
    debug_query = substitute_params(cypher_query, params)
    if logger.getEffectiveLevel() == logging.DEBUG:
            panel = Panel(
                Markdown(debug_query),
                border_style="blue",  # Keep blue border
                title="[TOOL DEBUGGING] Cypher Prompt dynamically compiled for NEO4J",
                title_align="left",
                expand=True,  # Expands panel width dynamically
            )            
            console.print(panel)

    try:
        # Execute the query using the graph.query() method
        results = graph.query(cypher_query, params)
        if not results:
            return "No RULAC data found."
        # Assume the first record contains the required RULAC_research field
        research_result = results[0].get("RULAC_research")
        # return research_result




        cleanedToolMessage = format_rulac_result(research_result)

        # print(f"CURRENT RESULT: {cleanedToolMessage}")
        panel = Panel(
            Markdown(cleanedToolMessage),
            style="green on white",  # black text on blue background for contrast
            border_style="black",  # Keep white border
            title="[TOOL INFO] RULAC CLEANED TOOL RESULTS",
            title_align="left",
            expand=True,  # Expands panel width dynamically
            )            
        console.print(panel)


        await collect_RULAC_citations_forOpenwebUI(self, research_result)


        # await collect_RULAC_citations_forOpenwebUI(self, direct_context_response)
        # print("Generated Query:", generated_query)

        return cleanedToolMessage






    except Exception as e:
        error_message = f"Error connecting to Neo4j: {e}"
        print(f"DEBUG: {error_message}")
        await __event_emitter__(
            {"type": "status", "data": {"description": error_message, "done": True}}
            )
        raise

