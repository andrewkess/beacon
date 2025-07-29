PROMPT = """
// Define the target organizations and conflict type(s)
WITH $target_organization_name AS target_organization_name, [] AS target_state_actor_UN_M49_codes,
     $target_conflict_types AS target_conflict_types

MATCH (org:Organization)
WHERE org.name IN target_organization_name
OPTIONAL MATCH (sa:StateActor)-[:IS_MEMBER]->(org)
OPTIONAL MATCH (sa)-[:IS_PARTY_TO_CONFLICT]->(c:Conflict)
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)
WITH sa, c, actor, ct, target_conflict_types, target_state_actor_UN_M49_codes, target_organization_name
WITH sa,
     COLLECT(DISTINCT c) AS all_conflicts,
     COLLECT(DISTINCT actor) AS all_actors,
     COLLECT(DISTINCT { conflict: c, type: ct.type }) AS all_conflict_types,
     target_conflict_types,
     target_state_actor_UN_M49_codes,
     target_organization_name
WITH sa,
     [conflict IN all_conflicts 
       WHERE conflict IS NOT NULL 
         AND (target_conflict_types IS NULL OR size(target_conflict_types)=0 OR 
              ANY(t IN target_conflict_types WHERE EXISTS((conflict)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(:ConflictType {type: t})))
         )
     ] AS conflicts,
     [item IN all_conflict_types 
       WHERE item.conflict IS NOT NULL 
         AND (target_conflict_types IS NULL OR size(target_conflict_types)=0 OR 
              ANY(t IN target_conflict_types WHERE item.type = t)
         )
     ] AS conflict_types,
     all_actors,
     target_conflict_types,
     target_state_actor_UN_M49_codes,
     target_organization_name
WITH COLLECT({
  state_actor_name: sa.name,
  state_actor_code: sa.UN_M49Code,
  conflicts: conflicts,
  all_actors: all_actors,
  conflict_types: conflict_types,
  conflict_count: size(conflicts)
}) AS state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes, target_organization_name
WITH apoc.coll.sortMaps(state_conflict_data, "conflict_count") AS sorted_state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes, target_organization_name
WITH CASE
  WHEN size(target_state_actor_UN_M49_codes)=0 AND size(target_conflict_types)=0 
  THEN sorted_state_conflict_data[0..10]
  ELSE sorted_state_conflict_data
END AS state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes, target_organization_name
WITH state_conflict_data,
     apoc.text.join(
       [d IN state_conflict_data 
         WHERE size(apoc.coll.toSet(d.conflicts)) > 0 |
         d.state_actor_name + " is a state actor to " + toString(size(apoc.coll.toSet(d.conflicts))) + " distinct armed conflict(s) (" +
         apoc.text.join(apoc.coll.toSet([conf IN d.conflicts | conf.name]), ", ") + ")"
       ],
       "; "
     ) AS breakdownText,
     apoc.coll.toSet(apoc.coll.flatten([d IN state_conflict_data | d.conflicts])) AS global_conflicts,
     target_conflict_types,
     target_state_actor_UN_M49_codes,
     target_organization_name
WITH breakdownText, 
     global_conflicts, 
     target_conflict_types,
     target_state_actor_UN_M49_codes,
     target_organization_name,
     size(global_conflicts) AS total_distinct_conflicts,
     state_conflict_data
WITH CASE
       WHEN total_distinct_conflicts = 0 THEN
         "According to RULAC, there are currently no recorded armed conflicts classified as " +
         apoc.text.join([x IN target_conflict_types | "'" + x + "'"], ", ") +
         " involving state actors that are members of the '" + apoc.text.join(target_organization_name, ", ") + "' organization."
       ELSE
         "According to RULAC, there are currently " + toString(total_distinct_conflicts) +
         " total distinct armed conflict(s) classified as " +
         apoc.text.join([x IN target_conflict_types | "'" + x + "'"], ", ") +
         " involving state actors that are members of the '" + apoc.text.join(target_organization_name, ", ") + "' organization. Breakdown by state actor: " + breakdownText + "."
     END AS summary_text, global_conflicts, state_conflict_data, target_conflict_types, target_state_actor_UN_M49_codes, target_organization_name
WITH summary_text,
     [conf IN global_conflicts | {
         conflict_name: COALESCE(conf.name, "Unknown"),
         conflict_classification: COALESCE(
           [item IN apoc.coll.flatten([d IN state_conflict_data | d.conflict_types])
            WHERE item.conflict = conf | item.type][0],
           "Unclassified"
         ),
         conflict_overview: COALESCE(conf.overview, "No Overview Available"),
         applicable_ihl_law: COALESCE(conf.applicable_law, "Not Specified"),
         conflict_citation: COALESCE(conf.citation, "No Citation Available"),
         state_parties: CASE 
                          WHEN size(apoc.coll.toSet(
                                 [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                  WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                                 ]
                               )) = 0 
                          THEN "No state actors recorded" 
                          ELSE apoc.text.join(
                                 apoc.coll.toSet(
                                   [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                    WHERE "StateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                                    | p.name]
                                 ),
                                 ", "
                               )
                        END,
         non_state_parties: CASE 
                              WHEN size(apoc.coll.toSet(
                                     [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                      WHERE "NonStateActor" IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                                     ]
                                   )) = 0 
                              THEN "No non-state actors recorded" 
                              ELSE apoc.text.join(
                                     apoc.coll.toSet(
                                       [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
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
} AS RULAC_research"""