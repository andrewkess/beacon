PROMPT = """
         // Step 0: Define target regions (by name) and conflict-type filters
    WITH $regions AS regions, 
         $target_conflict_types AS target_conflict_types


// Step A: Collect region data first (so we always have region_name)

MATCH (gr:GeoRegion)
WHERE gr.name IN regions
WITH target_conflict_types, regions,
     COLLECT({
       region_name: gr.name
     }) AS region_dictionary



// Step B: Retrieve countries in those target regions

MATCH (gr:GeoRegion)<-[:BELONGS_TO]-(co:Country)
WHERE gr.name IN regions
WITH co, gr.name AS region_code, gr.name AS region_name,
     regions, target_conflict_types, region_dictionary



// Step C: Match conflicts in those countries, along with classification & actors

OPTIONAL MATCH (co)<-[:IS_TAKING_PLACE_IN_COUNTRY]-(c:Conflict)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
WITH co, region_code, region_name, c, ct, actor,
     regions, target_conflict_types, region_dictionary



// Step D: Filter conflicts by desired conflict types (always apply even if no filter)

WITH co, region_code, region_name, regions, target_conflict_types, region_dictionary,
     [conflict IN COLLECT(DISTINCT c)
       WHERE conflict IS NOT NULL
         AND (
           // If no conflict_types given, keep all conflicts;
           // otherwise, check if this conflict matches at least one target type
           target_conflict_types IS NULL OR size(target_conflict_types) = 0
           OR ANY(t IN target_conflict_types
                  WHERE EXISTS((conflict)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(:ConflictType {type: t})))
         )
     ] AS conflicts,
     [item IN COLLECT(DISTINCT { conflict: c, type: ct.type })
       WHERE item.conflict IS NOT NULL
         AND (
           target_conflict_types IS NULL OR size(target_conflict_types) = 0
           OR ANY(t IN target_conflict_types WHERE item.type = t)
         )
     ] AS conflict_types,
     COLLECT(DISTINCT actor) AS all_actors



// Step E: Build per-country conflict data

WITH regions, target_conflict_types, region_dictionary,
     COLLECT({
       country_name:   co.name,
       region:         region_name,
       region_code:    region_code,
       conflicts:      conflicts,
       conflict_count: size(conflicts),
       conflict_names: [conf IN conflicts | conf.name],
       all_actors:     all_actors,
       conflict_types: conflict_types
     }) AS country_conflict_data



// Step F: Build region_conflicts, using ONLY the official region name

WITH country_conflict_data, target_conflict_types, region_dictionary, regions,
     [region IN regions |
       {
         region_code: region,
         // Always pull the official region name from region_dictionary
         region_name: [rd IN region_dictionary WHERE rd.region_name = region | rd.region_name][0],
         conflicts: apoc.coll.toSet(
           apoc.coll.flatten(
             [d IN country_conflict_data WHERE d.region_code = region | d.conflicts]
           )
         )
       }
     ] AS region_conflicts




// Step G: Count unique conflicts per region

WITH country_conflict_data, target_conflict_types,
     [r IN region_conflicts |
       {
         region_name:   r.region_name,
         conflict_count: size(r.conflicts)
       }
     ] AS region_conflict_counts



// Step H: Determine which region has the most conflicts (if > 1 region)

UNWIND region_conflict_counts AS r
WITH country_conflict_data, target_conflict_types, region_conflict_counts,
     COUNT(region_conflict_counts) AS region_count,
     MAX(r.conflict_count) AS max_conflict_count,
     COLLECT(r { .region_name, .conflict_count }) AS all_regions

// Collect all regions that tie for the max conflict count
WITH country_conflict_data, target_conflict_types, region_conflict_counts,
     region_count, max_conflict_count,
     [r IN all_regions WHERE r.conflict_count = max_conflict_count | r.region_name] AS leading_regions

// Build a short summary about “which region leads” or “tie” or “no conflicts”
WITH country_conflict_data, target_conflict_types, region_conflict_counts,
     max_conflict_count, leading_regions, region_count,
     CASE
       WHEN region_count = 1 OR max_conflict_count = 0 THEN ""
       WHEN region_count > 1 AND max_conflict_count = 0 THEN "Neither region has recorded conflicts."
       WHEN size(leading_regions) > 1 THEN
         "Both " + apoc.text.join(leading_regions, " and ") + " regions have the same number of recorded conflicts."
       ELSE
         leading_regions[0] + " has the most recorded conflicts."
     END AS dominant_region_summary



// Step I: Construct breakdown text by country

WITH country_conflict_data, region_conflict_counts, dominant_region_summary, target_conflict_types,
     apoc.text.join(
       [d IN country_conflict_data |
         CASE
           WHEN d.conflict_count = 0 THEN
             "No recorded conflicts in " + d.country_name + " (" + d.region + ")"
           WHEN d.conflict_count = 1 THEN
             "1 conflict taking place in " + d.country_name + " (" + d.region + "): " + apoc.text.join(d.conflict_names, ", ")
           ELSE
             toString(d.conflict_count) + " conflicts taking place in " + d.country_name + " (" + d.region + "): " +
             apoc.text.join(d.conflict_names, ", ")
         END
       ],
       "; "
     ) AS breakdownText



// Step J: Build partial string with CASE in a separate WITH

WITH country_conflict_data, region_conflict_counts, dominant_region_summary, breakdownText, target_conflict_types,

// This CASE statement is in its own step:
CASE 
  WHEN target_conflict_types IS NOT NULL AND size(target_conflict_types) > 0
  THEN
    "According to RULAC, among recorded conflicts classified as " +
    apoc.text.join(
      [x IN target_conflict_types | "'" + x + "'"],
      " and/or "
    )
  ELSE
    "According to RULAC, among recorded conflicts"
END AS initial_conflicts_string



// Step K: Construct final summary_text using the partial string

WITH initial_conflicts_string, region_conflict_counts, dominant_region_summary, breakdownText, country_conflict_data,

// Now concatenate in a simpler expression
initial_conflicts_string +
" taking place in " +
apoc.text.join([r IN region_conflict_counts | r.region_name], " and/or ") +
" --> " +
apoc.text.join(
  [r IN region_conflict_counts |
    CASE
      WHEN r.conflict_count = 0 THEN "No conflicts taking place in " + r.region_name + " region"
      WHEN r.conflict_count = 1 THEN "1 conflict is taking place in " + r.region_name + " region"
      ELSE toString(r.conflict_count) + " total distinct conflicts are currently taking place in " + r.region_name + " region"
    END
  ],
  ", "
) +
". " + dominant_region_summary +
" Breakdown by country: " + breakdownText
AS summary_text



// Step L: Prepare final conflict_details

WITH summary_text, country_conflict_data,
     apoc.coll.toSet(
       apoc.coll.flatten([d IN country_conflict_data | d.conflicts])
     ) AS global_conflicts

WITH summary_text,
     [conf IN global_conflicts |
       {
         conflict_name:           COALESCE(conf.name, "Unknown"),
         conflict_classification: COALESCE(
           [item IN apoc.coll.flatten([d IN country_conflict_data | d.conflict_types])
             WHERE item.conflict = conf | item.type][0],
           "Unclassified"
         ),
         conflict_overview:       COALESCE(conf.overview, "No Overview Available"),
         applicable_ihl_law:      COALESCE(conf.applicable_law, "Not Specified"),
         conflict_citation:       COALESCE(conf.citation, "No Citation Available"),
         state_parties: CASE
           WHEN size(apoc.coll.toSet(
             [p IN apoc.coll.flatten([d IN country_conflict_data | d.all_actors])
              WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)]
           )) = 0
           THEN "No state actors recorded"
           ELSE apoc.text.join(
             apoc.coll.toSet(
               [p IN apoc.coll.flatten([d IN country_conflict_data | d.all_actors])
                WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                | p.name]
             ),
             ", "
           )
         END,
         non_state_parties: CASE
           WHEN size(apoc.coll.toSet(
             [p IN apoc.coll.flatten([d IN country_conflict_data | d.all_actors])
              WHERE "NonStateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)]
           )) = 0
           THEN "No non-state actors recorded"
           ELSE apoc.text.join(
             apoc.coll.toSet(
               [p IN apoc.coll.flatten([d IN country_conflict_data | d.all_actors])
                WHERE "NonStateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                | p.name]
             ),
             ", "
           )
         END
       }
     ] AS conflict_details



// Final RETURN

RETURN {
  summary: summary_text,
  conflict_details: conflict_details
} AS RULAC_research
"""
