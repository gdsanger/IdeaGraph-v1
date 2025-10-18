"""
Example Usage of KiGate API Integration in IdeaGraph

This file demonstrates how to use the KiGate service to interact with AI agents.
"""

from core.services.kigate_service import KiGateService, KiGateServiceError


def example_basic_usage():
    """Basic example of using KiGateService"""
    try:
        # Initialize the service (uses settings from database)
        kigate = KiGateService()
        
        # List all available agents
        agents_response = kigate.get_agents()
        print("Available agents:")
        for agent in agents_response['agents']:
            print(f"  - {agent['name']}: {agent.get('description', 'No description')}")
        
    except KiGateServiceError as e:
        print(f"Error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")


def example_execute_agent():
    """Example of executing an agent"""
    try:
        kigate = KiGateService()
        
        # Execute a translation agent
        result = kigate.execute_agent(
            agent_name="translation-agent",
            provider="openai",
            model="gpt-4",
            message="Hello, how are you today?",
            user_id="christian.angermeier@isartec.de"
        )
        
        print(f"Job ID: {result['job_id']}")
        print(f"Status: {result['status']}")
        print(f"Result: {result['result']}")
        
    except KiGateServiceError as e:
        print(f"Error executing agent: {e.message}")


def example_execute_agent_with_parameters():
    """Example of executing an agent with custom parameters"""
    try:
        kigate = KiGateService()
        
        # Execute agent with parameters
        result = kigate.execute_agent(
            agent_name="translation-agent",
            provider="openai",
            model="gpt-4",
            message="Translate this text: Good morning, have a nice day!",
            user_id="christian.angermeier@isartec.de",
            parameters={
                "language": "German"
            }
        )
        
        print(f"Translation result: {result['result']}")
        
    except KiGateServiceError as e:
        print(f"Error: {e.message}")


def example_get_agent_details():
    """Example of getting detailed information about an agent"""
    try:
        kigate = KiGateService()
        
        # Get details of a specific agent
        details = kigate.get_agent_details("translation-agent")
        
        agent = details['agent']
        print(f"Agent: {agent['name']}")
        print(f"Description: {agent.get('description', 'N/A')}")
        print(f"Provider: {agent.get('provider', 'N/A')}")
        print(f"Model: {agent.get('model', 'N/A')}")
        print(f"Role: {agent.get('role', 'N/A')}")
        
        if 'parameters' in agent:
            print("Available parameters:")
            for param in agent['parameters']:
                print(f"  - {param}")
        
    except KiGateServiceError as e:
        print(f"Error: {e.message}")


def example_with_custom_settings():
    """Example of initializing service with specific settings"""
    from main.models import Settings
    
    try:
        # Get settings from database
        settings = Settings.objects.first()
        
        # Initialize service with specific settings
        kigate = KiGateService(settings=settings)
        
        # Use the service
        agents = kigate.get_agents()
        print(f"Found {len(agents['agents'])} agents")
        
    except KiGateServiceError as e:
        print(f"Error: {e.message}")


def example_error_handling():
    """Example of proper error handling"""
    try:
        kigate = KiGateService()
        
        # Try to execute with invalid parameters
        result = kigate.execute_agent(
            agent_name="non-existent-agent",
            provider="openai",
            model="gpt-4",
            message="Test message",
            user_id="test-user"
        )
        
    except KiGateServiceError as e:
        # Handle specific error
        if e.status_code == 404:
            print("Agent not found")
        elif e.status_code == 401:
            print("Authentication failed")
        elif e.status_code == 408:
            print("Request timed out")
        elif e.status_code == 503:
            print("Service unavailable")
        else:
            print(f"Error: {e.message}")
        
        # Get structured error response
        error_dict = e.to_dict()
        print(f"Error details: {error_dict}")


if __name__ == "__main__":
    print("=== Example 1: List all agents ===")
    example_basic_usage()
    
    print("\n=== Example 2: Execute an agent ===")
    example_execute_agent()
    
    print("\n=== Example 3: Execute with parameters ===")
    example_execute_agent_with_parameters()
    
    print("\n=== Example 4: Get agent details ===")
    example_get_agent_details()
    
    print("\n=== Example 5: Error handling ===")
    example_error_handling()
