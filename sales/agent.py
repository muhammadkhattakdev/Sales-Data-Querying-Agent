import os
import sqlite3
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from django.conf import settings

class AgentState(TypedDict):
    question: str
    sql_query: str
    query_result: str
    final_answer: str
    error: str

# Initialize the LLM
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
        temperature=0
    )

# Node 1: Generate SQL Query
def generate_sql(state: AgentState) -> AgentState:
    """Generate SQL query from natural language question"""
    llm = get_llm()
    
    schema_info = """
    Table: sales_sale
    Columns:
    - id: INTEGER (Primary Key)
    - date: DATE
    - price_sold: DECIMAL(10,2)
    - price_purchased: DECIMAL(10,2)
    - product_name: VARCHAR(200)
    
    Note: Profit = price_sold - price_purchased
    """
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system", """You are a SQL expert. Generate a SQLite query based on the user's question.
        
                Database Schema:
                {schema}

                Rules:
                1. Return ONLY the SQL query, nothing else
                2. Use proper SQLite syntax
                3. For date filtering, use date() function
                4. For "this month", use: WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
                5. For profit calculations, use: (price_sold - price_purchased)
                6. Always use proper column names as shown in schema
                7. Do not use markdown formatting or code blocks

                Examples:
                Question: "How much profit did product ABC make this month?"
                Query: SELECT SUM(price_sold - price_purchased) as total_profit FROM sales_sale WHERE product_name = 'ABC' AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')

                Question: "What are total sales for product XYZ?"
                Query: SELECT COUNT(*) as total_sales, SUM(price_sold) as total_revenue FROM sales_sale WHERE product_name = 'XYZ' """), 
                ("human", "{question}")
    ])
    
    try:
        chain = prompt | llm
        response = chain.invoke({
            "schema": schema_info,
            "question": state["question"]
        })
        
        sql_query = response.content.strip()
        # Clean up any markdown formatting
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        state["sql_query"] = sql_query
        state["error"] = ""
    except Exception as e:
        state["error"] = f"Error generating SQL: {str(e)}"
    
    return state

# Node 2: Execute SQL Query
def execute_sql(state: AgentState) -> AgentState:
    """Execute the generated SQL query"""
    if state.get("error"):
        return state

    try:
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(state["sql_query"])
        results = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        
        conn.close()
        
        # Format results
        if results:
            formatted_results = []
            for row in results:
                row_dict = dict(zip(column_names, row))
                formatted_results.append(row_dict)
            state["query_result"] = str(formatted_results)
        else:
            state["query_result"] = "No results found"
            
    except Exception as e:
        state["error"] = f"Error executing SQL: {str(e)}"
    
    return state

# Node 3: Generate Natural Language Response
def generate_response(state: AgentState) -> AgentState:
    """Generate a natural language response from query results"""
    if state.get("error"):
        state["final_answer"] = f"I encountered an error: {state['error']}"
        return state
    
    llm = get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that explains database query results in natural language.

            Given the user's question and the query results, provide a clear, concise answer.
            Format numbers nicely (e.g., currency with $ and 2 decimal places).
            If no results were found, say so politely."""),
                    ("human", """Question: {question}

            Query Results: {results}
                     
            Provide a natural language answer:""")
    ])

    try:
        chain = prompt | llm
        response = chain.invoke({
            "question": state["question"],
            "results": state["query_result"]
        })
        
        state["final_answer"] = response.content.strip()
    except Exception as e:
        state["final_answer"] = f"Error generating response: {str(e)}"
    
    return state

# Build the LangGraph workflow
def create_sales_agent():
    """Create and compile the LangGraph agent"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("execute_sql", execute_sql)
    workflow.add_node("generate_response", generate_response)
    
    # Add edges
    workflow.set_entry_point("generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_edge("execute_sql", "generate_response")
    workflow.add_edge("generate_response", END)
    
    return workflow.compile()

# Main function to query sales
def query_sales(question: str) -> dict:
    """Main function to process natural language queries about sales"""
    agent = create_sales_agent()
    
    initial_state = {
        "question": question,
        "sql_query": "",
        "query_result": "",
        "final_answer": "",
        "error": ""
    }
    
    result = agent.invoke(initial_state)
    
    return {
        "question": result["question"],
        "answer": result["final_answer"],
        "sql_query": result["sql_query"],
        "raw_results": result["query_result"]
    }
