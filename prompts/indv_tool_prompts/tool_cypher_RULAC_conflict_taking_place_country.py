PROMPT = """// Define the target country UN M49 codes and conflict type(s)
WITH $target_country_UN_M49_codes AS target_country_UN_M49_codes, 
     $target_conflict_types AS target_conflict_types

// Ensure we always get a Country node by matching the Country nodes first.
MATCH (co:Country)
WHERE (size(target_country_UN_M49_codes) = 0 OR co.UN_M49Code IN target_country_UN_M49_codes)

// MATCH to retrieve all conflicts taking place in that country, along with any related actors and conflict types.
OPTIONAL MATCH (co)<-[:IS_TAKING_PLACE_IN_COUNTRY]-(c:Conflict)
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)
WITH co, c, actor, ct, target_conflict_types, target_country_UN_M49_codes

// Collect all conflict data—even if some conflicts don’t match the target type.
WITH co,
     COLLECT(DISTINCT c) AS all_conflicts,
     COLLECT(DISTINCT actor) AS all_actors,
     COLLECT(DISTINCT { conflict: c, type: ct.type }) AS all_conflict_types,
     target_conflict_types,
     target_country_UN_M49_codes

// Filter the collected lists via list comprehensions so that only conflicts
// with a matching ConflictType are retained (or all conflicts if no type is specified).
WITH co,
     [conflict IN all_conflicts 
       WHERE conflict IS NOT NULL 
         AND ( target_conflict_types IS NULL 
               OR size(target_conflict_types) = 0 
               OR ANY(t IN target_conflict_types 
                      WHERE EXISTS((conflict)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(:ConflictType {type: t}))
                     )
         )
     ] AS conflicts,
     [item IN all_conflict_types 
       WHERE item.conflict IS NOT NULL 
         AND ( target_conflict_types IS NULL 
               OR size(target_conflict_types) = 0 
               OR ANY(t IN target_conflict_types WHERE item.type = t)
         )
     ] AS conflict_types,
     all_actors,
     target_conflict_types,
     target_country_UN_M49_codes

// Build the country data—ensuring one row per Country.
WITH COLLECT({
  country_name: co.name,
  country_code: co.UN_M49Code,
  conflicts: conflicts,
  conflict_count: size(conflicts),
  conflict_names: [conf IN conflicts | conf.name],
  all_actors: all_actors,
  conflict_types: conflict_types
}) AS country_conflict_data, target_conflict_types, target_country_UN_M49_codes


// Order the countries by conflict_count in ascending or descending order depnding on question
// Either in ascending order for top ranking of most conflicts taking place in countries 

// descending order option for bottom ranking, fewest conflicts or least number of conflicts taking place in countries:
// WITH reverse(apoc.coll.sortMaps(country_conflict_data, "conflict_count")) AS sorted_country_conflict_data,
//     target_conflict_types,
//     target_country_UN_M49_codes

// Ascending order option
WITH apoc.coll.sortMaps(country_conflict_data, "conflict_count") AS sorted_country_conflict_data,
     target_conflict_types,
     target_country_UN_M49_codes



//  limit to 10 countries if no specific UN_M49 codes or conflict types are provided
WITH CASE
  WHEN size(target_country_UN_M49_codes) = 0 AND size(target_conflict_types) = 0 
  THEN sorted_country_conflict_data[0..10] // use another limit for 10 if directly mentioned in question, eg. "top five countries" would become "sorted_country_conflict_data[0..5]"
  ELSE sorted_country_conflict_data
END AS country_conflict_data,
     target_conflict_types,
     target_country_UN_M49_codes

// Construct a breakdown text using the retrieved country details.
WITH country_conflict_data, target_conflict_types,
    apoc.text.join(
      [d IN country_conflict_data WHERE d.conflict_count > 0 |
        toString(d.conflict_count) + " conflict(s) taking place in " + d.country_name + " (" +  
        apoc.text.join(d.conflict_names, ", ") + ")"
      ],
      "; "
    ) AS breakdownText,

     apoc.coll.toSet(apoc.coll.flatten([d IN country_conflict_data | d.conflicts])) AS global_conflicts

// Count total distinct conflicts and prepare summary data.
WITH breakdownText, global_conflicts, target_conflict_types,
     size(global_conflicts) AS total_distinct_conflicts, country_conflict_data
WITH CASE
       WHEN total_distinct_conflicts = 0 THEN
         "According to RULAC, there are currently no recorded armed conflicts" +
         (CASE WHEN target_conflict_types IS NOT NULL AND size(target_conflict_types) > 0 THEN
           " classified as " + apoc.text.join([x IN target_conflict_types | "'" + x + "'"], " and/or ") ELSE "" END) +
         " taking place in the following countries: " + 
         apoc.text.join(apoc.coll.toSet([d IN country_conflict_data | d.country_name]), ", ") + "."
       ELSE
         "According to RULAC, there are currently " + toString(total_distinct_conflicts) +
         " total distinct armed conflict(s)" +
         (CASE WHEN target_conflict_types IS NOT NULL AND size(target_conflict_types) > 0 THEN
           " classified as " + apoc.text.join([x IN target_conflict_types | "'" + x + "'"], " and/or ") ELSE "" END) +
         " taking place in the following countries: " + 
         apoc.text.join(apoc.coll.toSet([d IN country_conflict_data WHERE d.conflict_count > 0 | d.country_name]), ", ") +
         ". Breakdown by country: " + breakdownText + "."
     END AS summary_text, global_conflicts, country_conflict_data


// Prepare detailed conflict information for each distinct conflict.
WITH summary_text, [conf IN global_conflicts | {
    conflict_name:           COALESCE(conf.name, "Unknown"),
    conflict_classification: COALESCE(
       [item IN apoc.coll.flatten([d IN country_conflict_data | d.conflict_types])
         WHERE item.conflict = conf | item.type][0],
       "Unclassified"
    ),
    conflict_overview:       COALESCE(conf.overview, "No Overview Available"),
    applicable_ihl_law:      COALESCE(conf.applicable_law, "Not Specified"),
    conflict_citation:       COALESCE(conf.citation, "No Citation Available"),
    state_parties:           CASE 
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
    non_state_parties:       CASE 
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
}] AS conflict_details

// Return final structured result
RETURN {
  summary: summary_text,
  conflict_details: conflict_details
} AS RULAC_research"""