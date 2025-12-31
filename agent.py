from dotenv import load_dotenv
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# 1. Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, max_tokens=300)

# 2. Define the State for the graph
# We add 'next_node' to hold the decision from our new initial router.


class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    next_node: str | None


# 3. Define the Pydantic models for routing and classification
class InitialRouter(BaseModel):
    """Determine whether to continue conversation or classify a user query."""

    next_node: Literal["receptionist", "classifier"] = Field(
        ...,
        description="Choose 'classifier' if the user presents a clear technical or financial question. Otherwise, choose 'receptionist'.",
    )


class MessageClassifier(BaseModel):
    """Classify the user's query into technical or financial."""

    message_type: Literal["technical", "financial"] = Field(
        ...,
        description="Classify the message as 'technical' or 'financial'.",
    )


# 4. Define the Graph Nodes
def route_initial_message(state: State):
    """
    This is the gatekeeper. It decides if a message is a simple greeting
    or a real query that needs classification.
    """
    last_message = state["messages"][-1]

    # Use the LLM to decide for all messages
    router_llm = llm.with_structured_output(InitialRouter)
    result = router_llm.invoke(
        [
            {
                "role": "system",
                "content": """You are an expert at routing user messages.
                If the message is a simple greeting, a thank you, or conversational fluff, route to the 'receptionist'.
                If the message contains a specific question or problem about technical or financial issues, route to the 'classifier'.""",
            },
            {"role": "user", "content": last_message.content},
        ]
    )
    return {"next_node": result.next_node}


def receptionist_agent(state: State):
    """
    A friendly agent that handles greetings and asks how it can help.
    """
    last_message = state["messages"][-1]
    messages = [
        {
            "role": "system",
            "content": "You are a friendly and helpful AI receptionist for a customer service center. Greet the user, and ask them how you can help with their technical or financial questions. Keep your responses brief and polite.",
        },
        {"role": "user", "content": last_message.content},
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def classify_message(state: State):
    """
    (Previously the first step) Now only runs when the initial router
    identifies a real query.
    """
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    result = classifier_llm.invoke(
        [
            {
                "role": "system",
                "content": """Classify the user message as either:
            - 'technical': if it asks for technical support, internet issues, message error, login problems, or any technical assistance
            - 'financial': if it asks for financial information, prices, billing, or payment issues
            """,
            },
            {"role": "user", "content": last_message.content},
        ]
    )

    return {"message_type": result.message_type}


def financial_agent(state: State):
    """Specialist agent for financial queries."""
    last_message = state["messages"][-1]
    messages = [
        {
            "role": "system",
            "content": "You are a financial support specialist. Your mission is to help customers with billing, payment, and refund questions in an empathetic and precise manner.",
        },
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


def technical_agent(state: State):
    """Specialist agent for technical queries."""
    last_message = state["messages"][-1]
    messages = [
        {
            "role": "system",
            "content": "You are a technical support specialist. Your mission is to help customers with technical issues, internet problems, message errors, and login issues in a clear and helpful manner.",
        },
        {"role": "user", "content": last_message.content},
    ]

    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}


# 5. Define the Conditional Routing Logic
def specialist_router(state: State):
    """Reads the 'message_type' to route to the correct specialist."""

    return state.get("message_type")


# 6. Build the New Graph

graph_builder = StateGraph(State)

# Add all the functions as nodes

graph_builder.add_node("initial_router", route_initial_message)
graph_builder.add_node("receptionist", receptionist_agent)
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("technical", technical_agent)
graph_builder.add_node("financial", financial_agent)

# The graph now starts at our new 'initial_router'
graph_builder.add_edge(START, "initial_router")

# This first conditional edge decides between the receptionist and the classifier
graph_builder.add_conditional_edges(
    "initial_router",
    lambda state: state.get("next_node"),
    {"receptionist": "receptionist", "classifier": "classifier"},
)

# This second conditional edge routes to the correct specialist
graph_builder.add_conditional_edges(
    "classifier",
    specialist_router,
    {"technical": "technical", "financial": "financial"},
)
# Define where the graph ends
graph_builder.add_edge("receptionist", END)
graph_builder.add_edge("technical", END)
graph_builder.add_edge("financial", END)

# Compile the graph
app = graph_builder.compile()
