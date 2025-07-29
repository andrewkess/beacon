from neo4j import GraphDatabase

# Connection details
uri = "bolt://localhost:7687"  # Adjust to your Neo4j instance
username = "neo4j"
password = "password"

# Initialize the Neo4j driver
driver = GraphDatabase.driver(uri, auth=(username, password))

def run_query(query, parameters=None):
    """
    Run a Cypher query and return the results.
    """
    with driver.session() as session:
        result = session.run(query, parameters)
        return [record.data() for record in result]

# Test the connection and query
if __name__ == "__main__":
    try:
        # Cypher query to fetch nodes with label `Conflict`
        query = "MATCH (n:Conflict) RETURN n LIMIT 25"
        result = run_query(query)
        
        print("Query Results:")
        for record in result:
            print(record)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()
