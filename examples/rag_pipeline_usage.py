"""
RAG Pipeline Usage Examples for IdeaGraph Chat

This script demonstrates how to use the RAG pipeline for chat question answering.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
django.setup()

from chat.rag_pipeline import RAGPipeline, RAGPipelineError


def example_basic_usage():
    """Basic usage example"""
    print("=" * 60)
    print("Example 1: Basic Question Processing")
    print("=" * 60)
    
    try:
        # Initialize pipeline
        pipeline = RAGPipeline()
        
        # Process a question
        question = "Was ist RAG und wie funktioniert es?"
        result = pipeline.process_question(
            question=question,
            item_id=None,  # No specific item context
            tenant=None
        )
        
        # Display results
        print(f"\nQuestion: {question}")
        print(f"Success: {result['success']}")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nMetrics:")
        print(f"  - Semantic hits: {result['hits_sem']}")
        print(f"  - Keyword hits: {result['hits_kw']}")
        print(f"  - Final results: {result['hits_final']}")
        print(f"  - Processing time: {result['total_time']:.2f}s")
        print(f"  - Token estimate: {result['token_estimate']}")
        
    except RAGPipelineError as e:
        print(f"Pipeline error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")


def example_with_item_context():
    """Example with item-specific context"""
    print("\n" + "=" * 60)
    print("Example 2: Question with Item Context")
    print("=" * 60)
    
    try:
        pipeline = RAGPipeline()
        
        # Process question with item context
        question = "Welche Aufgaben sind noch offen?"
        item_id = "64b7cff1-d694-459e-8902-e132ab3fb137"  # Example item ID
        
        result = pipeline.process_question(
            question=question,
            item_id=item_id,
            tenant=None
        )
        
        print(f"\nQuestion: {question}")
        print(f"Item Context: {item_id}")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nSources used:")
        for source in result.get('sources', [])[:3]:
            print(f"  - [{source.get('type')}] {source.get('title', 'Untitled')}")
            print(f"    Score: {source.get('final_score', 0):.2f}")
        
    except RAGPipelineError as e:
        print(f"Pipeline error: {e.message}")


def example_step_by_step():
    """Step-by-step pipeline execution"""
    print("\n" + "=" * 60)
    print("Example 3: Step-by-Step Pipeline")
    print("=" * 60)
    
    try:
        pipeline = RAGPipeline()
        question = "Wie implementiere ich eine RAG-Pipeline?"
        
        # Step 1: Optimize question
        print("\nStep 1: Optimizing question...")
        expanded = pipeline.optimize_question(question)
        print(f"  Core: {expanded['core']}")
        print(f"  Synonyms: {expanded.get('synonyms', [])[:3]}")
        print(f"  Tags: {expanded.get('tags', [])[:3]}")
        
        # Step 2: Semantic retrieval
        print("\nStep 2: Semantic search...")
        results_sem = pipeline.retrieve_semantic(expanded)
        print(f"  Found {len(results_sem)} semantic results")
        
        # Step 3: Keyword retrieval
        print("\nStep 3: Keyword search...")
        results_kw = pipeline.retrieve_keywords(expanded)
        print(f"  Found {len(results_kw)} keyword results")
        
        # Step 4: Fusion and reranking
        print("\nStep 4: Fusing and reranking...")
        final_results = pipeline.fuse_and_rerank(
            results_sem, 
            results_kw, 
            expanded
        )
        print(f"  Top {len(final_results)} results after fusion")
        
        # Step 5: Assemble context
        print("\nStep 5: Assembling context...")
        context = pipeline.assemble_context(final_results)
        print(f"  Context length: {len(context)} characters")
        print(f"  Token estimate: {len(context.split())} words")
        
        # Step 6: Generate answer
        print("\nStep 6: Generating answer...")
        answer = pipeline.send_to_answering_agent(question, context)
        print(f"\nFinal Answer:\n{answer}")
        
    except RAGPipelineError as e:
        print(f"Pipeline error: {e.message}")


def example_optimization_only():
    """Example showing just question optimization"""
    print("\n" + "=" * 60)
    print("Example 4: Question Optimization Only")
    print("=" * 60)
    
    try:
        pipeline = RAGPipeline()
        
        questions = [
            "Was ist ein Task?",
            "Wie erstelle ich einen neuen Milestone?",
            "Zeige mir alle offenen Issues"
        ]
        
        for question in questions:
            print(f"\nOriginal: {question}")
            expanded = pipeline.optimize_question(question)
            print(f"  Core: {expanded['core']}")
            print(f"  Language: {expanded['language']}")
            print(f"  Tags: {', '.join(expanded.get('tags', [])[:5])}")
            if expanded.get('followup_questions'):
                print(f"  Follow-up: {expanded['followup_questions'][0]}")
        
    except RAGPipelineError as e:
        print(f"Pipeline error: {e.message}")


def example_error_handling():
    """Example demonstrating error handling"""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)
    
    try:
        # Test with empty question
        pipeline = RAGPipeline()
        result = pipeline.process_question("")
        
        if result['success']:
            print("Pipeline handled empty question gracefully")
            print(f"Answer: {result['answer']}")
        else:
            print(f"Error: {result.get('error')}")
        
    except Exception as e:
        print(f"Exception caught: {str(e)}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("RAG Pipeline Usage Examples")
    print("=" * 60)
    
    # Run all examples
    example_basic_usage()
    example_with_item_context()
    example_step_by_step()
    example_optimization_only()
    example_error_handling()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
