PROMPT = """// Define target NSAs
WITH $target_non_state_actor_name_and_aliases AS target_non_state_actor_name_and_aliases

// Step 1: Identify the relevant NonStateActor(s) that match any of the given name/aliases
OPTIONAL MATCH (nsa:NonStateActor)
WHERE ANY(name_alias IN target_non_state_actor_name_and_aliases 
          WHERE toLower(nsa.name) CONTAINS toLower(name_alias)
             OR ANY(alias IN nsa.aliases WHERE toLower(alias) CONTAINS toLower(name_alias)))

// Step 2: Retrieve all conflicts involving these NonStateActors
OPTIONAL MATCH (nsa)-[:IS_PARTY_TO_CONFLICT]->(c:Conflict)
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)
WITH nsa, c, actor, ct

// Step 3: Collect all conflict data
WITH nsa,
     COLLECT(DISTINCT c) AS all_conflicts,
     COLLECT(DISTINCT actor) AS all_actors,
     COLLECT(DISTINCT { conflict: c, type: ct.type }) AS all_conflict_types

// Step 4: Build NonStateActor conflict data
WITH COLLECT({
  non_state_actor_name: nsa.name,
  conflicts: all_conflicts,
  all_actors: all_actors,
  conflict_types: all_conflict_types
}) AS non_state_actor_conflict_data

// Step 5: Flatten conflicts and prepare summary info
WITH non_state_actor_conflict_data,
     apoc.coll.toSet(apoc.coll.flatten([d IN non_state_actor_conflict_data | d.conflicts])) AS global_conflicts
WITH size(global_conflicts) AS total_distinct_conflicts,
     apoc.text.join([gc IN global_conflicts | gc.name], ", ") AS conflict_names_list,
     non_state_actor_conflict_data,
     global_conflicts

// Step 6: Build the summary text, now including the dynamic non-state actor names
WITH apoc.text.join($target_non_state_actor_name_and_aliases, ", ") AS non_state_actor_names,
     total_distinct_conflicts, conflict_names_list, non_state_actor_conflict_data, global_conflicts
WITH CASE
       WHEN total_distinct_conflicts = 0 THEN
         "According to RULAC, there are currently no recorded armed conflicts involving " + non_state_actor_names + "."
       ELSE
         "According to RULAC, there are currently " + toString(total_distinct_conflicts) +
         " total distinct armed conflict(s) involving " + non_state_actor_names + " as a non-state actor. " +
         "These conflicts are: " + conflict_names_list + "."
     END AS summary_text,
     global_conflicts,
     non_state_actor_conflict_data


// Step 7: Prepare detailed conflict information
WITH summary_text,
     [conf IN global_conflicts | {
       conflict_name: COALESCE(conf.name, "Unknown"),
       conflict_classification: COALESCE(
         [item IN apoc.coll.flatten([d IN non_state_actor_conflict_data | d.conflict_types])
          WHERE item.conflict = conf | item.type][0],
         "Unclassified"
       ),
       conflict_overview: COALESCE(conf.overview, "No Overview Available"),
       applicable_ihl_law: COALESCE(conf.applicable_law, "Not Specified"),
       conflict_citation: COALESCE(conf.citation, "No Citation Available"),
       state_parties: CASE
         WHEN size(apoc.coll.toSet(
           [p IN apoc.coll.flatten([d IN non_state_actor_conflict_data | d.all_actors])
            WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)]
         )) = 0
         THEN "No state actors recorded"
         ELSE apoc.text.join(
           apoc.coll.toSet(
             [p IN apoc.coll.flatten([d IN non_state_actor_conflict_data | d.all_actors])
              WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
              | p.name]
           ),
           ", "
         )
       END,
       non_state_parties: CASE
         WHEN size(apoc.coll.toSet(
           [p IN apoc.coll.flatten([d IN non_state_actor_conflict_data | d.all_actors])
            WHERE "NonStateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)]
         )) = 0
         THEN "No non-state actors recorded"
         ELSE apoc.text.join(
           apoc.coll.toSet(
             [p IN apoc.coll.flatten([d IN non_state_actor_conflict_data | d.all_actors])
              WHERE "NonStateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
              | p.name]
           ),
           ", "
         )
       END
     }] AS conflict_details

RETURN {
  summary: summary_text,
  conflict_details: conflict_details
} AS RULAC_research
"""