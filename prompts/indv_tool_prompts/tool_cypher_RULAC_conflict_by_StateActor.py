PROMPT = """// Define the target state actor(s) and optional conflict type(s)
WITH $countries AS target_countries, 
     $conflict_types AS target_conflict_types

// Match the state actor(s) by name or alias
MATCH (sa:StateActor)
WHERE (size(target_countries) = 0 OR 
       ANY(country IN target_countries 
           WHERE toLower(sa.name) CONTAINS toLower(country)
              OR ANY(alias IN sa.aliases WHERE toLower(alias) CONTAINS toLower(country))
       )
)

// OPTIONAL MATCH to get all related conflicts, their actors, and conflict types
OPTIONAL MATCH (sa)-[:IS_PARTY_TO_CONFLICT]->(c:Conflict)
OPTIONAL MATCH (c)-[:IS_PARTY_TO_CONFLICT]-(actor)
OPTIONAL MATCH (c)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(ct:ConflictType)
WITH sa, c, actor, ct, target_conflict_types, target_countries

// Collect all conflict data—even if some conflicts don't match the target type
WITH sa,
     COLLECT(DISTINCT c) AS all_conflicts,
     COLLECT(DISTINCT actor) AS all_actors,
     COLLECT(DISTINCT { conflict: c, type: ct.type }) AS all_conflict_types,
     target_conflict_types,
     target_countries

// Now filter the collected lists to only include conflicts that match the criteria.
WITH sa,
     [conflict IN all_conflicts 
       WHERE conflict IS NOT NULL 
         AND ( target_conflict_types IS NULL 
               OR size(target_conflict_types)=0 
               OR ANY(t IN target_conflict_types 
                      WHERE EXISTS((conflict)-[:IS_CLASSIFIED_AS_CONFLICT_TYPE]->(:ConflictType {type: t}))
                     )
         )
     ] AS conflicts,
     [item IN all_conflict_types 
       WHERE item.conflict IS NOT NULL 
         AND ( target_conflict_types IS NULL 
               OR size(target_conflict_types)=0 
               OR ANY(t IN target_conflict_types WHERE item.type = t)
         )
     ] AS conflict_types,
     all_actors,
     target_conflict_types,
     target_countries

// Build the state actor data—ensuring one row per state actor
WITH COLLECT({
  state_actor_name: sa.name,
  state_actor_code: sa.UN_M49Code,
  conflicts: conflicts,
  all_actors: all_actors,
  conflict_types: conflict_types,
  conflict_count: size(conflicts)
}) AS state_conflict_data, target_conflict_types, target_countries

// Order the state actors by conflict count in ascending order (for top rankings)
WITH apoc.coll.sortMaps(state_conflict_data, 'conflict_count') AS sorted_state_conflict_data, target_conflict_types, target_countries

// Limit to the top 10 state actors if no specific filters provided
WITH CASE 
  WHEN size(target_countries) = 0 AND size(target_conflict_types) = 0 
  THEN sorted_state_conflict_data[0..10]
  ELSE sorted_state_conflict_data
END AS state_conflict_data, target_conflict_types, target_countries

// **** Modified Summary Generation ****
// Unwind the state_conflict_data for individual processing.
UNWIND state_conflict_data AS actorData
WITH actorData, state_conflict_data, target_conflict_types, target_countries
WITH actorData, state_conflict_data, target_conflict_types, target_countries,
     CASE 
       WHEN size(target_conflict_types) = 0 
         THEN [ { type: null, count: actorData.conflict_count, conflicts: actorData.conflicts } ]
       ELSE
         [ t IN target_conflict_types | 
           { type: t, 
             conflicts: [conf IN actorData.conflicts 
                          WHERE ANY(ct IN actorData.conflict_types 
                                    WHERE ct.conflict = conf AND toLower(ct.type) = toLower(t)
                                 )
                         ],
             count: size([conf IN actorData.conflicts 
                           WHERE ANY(ct IN actorData.conflict_types 
                                     WHERE ct.conflict = conf AND toLower(ct.type) = toLower(t)
                                  )
                          ])
           }
         ]
     END AS classificationDetails

WITH actorData.state_actor_name AS stateActor, classificationDetails, state_conflict_data, target_conflict_types, target_countries
WITH stateActor, 
     apoc.text.join(
        [ cd IN classificationDetails | 
           stateActor + ' is involved as a state actor to ' + toString(cd.count) + ' armed conflict' + 
           (CASE WHEN cd.count = 1 THEN '' ELSE 's' END) +
           (CASE WHEN cd.type IS NOT NULL THEN ' classified as "' + cd.type + '"' ELSE '' END) +
           (CASE WHEN cd.count > 0 THEN ': ' + apoc.text.join([conf IN cd.conflicts WHERE conf IS NOT NULL | conf.name], ', ') ELSE '' END)
        ],
        '. '
     ) AS actorSummaryText, state_conflict_data, target_conflict_types, target_countries

// Build overall summary text using all non-zero state actor summaries.
WITH 'According to RULAC, ' + apoc.text.join(collect(actorSummaryText), '. ') + '.' AS summary_text,
     apoc.coll.toSet(apoc.coll.flatten([d IN state_conflict_data | d.conflicts])) AS global_conflicts,
     state_conflict_data

// Prepare detailed conflict information.
WITH summary_text, global_conflicts, state_conflict_data,
     [conf IN global_conflicts | {
         conflict_name: COALESCE(conf.name, 'Unknown'),
         conflict_classification: COALESCE(
           [item IN apoc.coll.flatten([d IN state_conflict_data | d.conflict_types])
            WHERE item.conflict = conf | item.type][0],
           'Unclassified'
         ),
         conflict_overview: COALESCE(conf.overview, 'No Overview Available'),
         applicable_ihl_law: COALESCE(conf.applicable_law, 'Not Specified'),
         conflict_citation: COALESCE(conf.citation, 'No Citation Available'),
         state_parties: CASE 
                          WHEN SIZE(apoc.coll.toSet(
                                 [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                  WHERE 'StateActor' IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)]
                               )) = 0 
                          THEN 'No state actors recorded' 
                          ELSE apoc.text.join(
                                 apoc.coll.toSet(
                                   [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                    WHERE 'StateActor' IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                                    | p.name]
                                 ),
                                 ', '
                               )
                        END,
         non_state_parties: CASE 
                              WHEN SIZE(apoc.coll.toSet(
                                     [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                      WHERE 'NonStateActor' IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)]
                                   )) = 0 
                              THEN 'No non-state actors recorded' 
                              ELSE apoc.text.join(
                                     apoc.coll.toSet(
                                       [p IN apoc.coll.flatten([d IN state_conflict_data | d.all_actors])
                                        WHERE 'NonStateActor' IN labels(p) AND (p)-[:IS_PARTY_TO_CONFLICT]->(conf)
                                        | p.name]
                                     ),
                                     ', '
                                   )
                            END
     }] AS conflict_details

RETURN {
  summary: summary_text,
  conflict_details: conflict_details
} AS RULAC_research
"""
