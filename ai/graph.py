from langgraph.graph import StateGraph,START,END
from ai.agents.state import InterviewState
from ai.agents import planner,retriever,generator,evaluator,coach
from langgraph.graph.state import CompiledStateGraph

def route_after_eval(state:InterviewState)->str:
    answered = len(state['evaluations'])
    total = sum(c['question_count'] for c in state['interview_plan'])
    return 'end' if answered >= total else 'continue'

def build_graph() -> CompiledStateGraph:
    g = StateGraph(InterviewState)
    g.add_node('planner',   planner.planner_agent)
    g.add_node('retriever', retriever.retriever_agent)
    g.add_node('generator', generator.question_generator)
    g.add_node('evaluator', evaluator.evaluator_agent)
    g.add_node('coach',     coach.coach_agent)

    g.add_edge(START,"planner")
    g.add_edge('planner',   'retriever')
    g.add_edge('retriever', 'generator')
    g.add_edge('generator', 'evaluator')

    g.add_conditional_edges('evaluator', route_after_eval, {
        'continue': 'retriever',  # More questions remain — loop back
        'end':      'coach',      # All questions done — generate report
        })
    g.add_edge('coach', END)

    return g.compile()


# Singleton graph instance
interview_graph = build_graph()