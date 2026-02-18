"""
Create a test workflow matching the user's image:

Silver Touch (trigger)
  ├── Ahmedabad
  │   ├── AI
  │   │   └── Hello from AI
  │   └── PHP
  ├── Delhi
  └── Canada
"""
from sqlalchemy.orm import Session
from database import SessionLocal
from app.models.chatbot import Chatbot
from app.models.workflow import Workflow
from app.models.node import Node
from app.models.edge import Edge


def create_test_workflow():
    """Create a test workflow"""
    db: Session = SessionLocal()
    try:
        # 1. Create or get chatbot
        chatbot = db.query(Chatbot).first()
        if not chatbot:
            chatbot = Chatbot(name="Test Chatbot", description="Test chatbot for workflow demo")
            db.add(chatbot)
            db.commit()
            db.refresh(chatbot)
            print(f"✓ Created chatbot: {chatbot.name} (ID: {chatbot.id})")
        else:
            print(f"✓ Using existing chatbot: {chatbot.name} (ID: {chatbot.id})")

        # 2. Create workflow
        workflow = Workflow(
            chatbot_id=chatbot.id,
            name="Silver Touch Workflow",
            is_active=True
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        print(f"✓ Created workflow: {workflow.name} (ID: {workflow.id})")

        # 3. Create nodes
        nodes = {}
        
        # Trigger node
        nodes['silver_touch'] = Node(
            workflow_id=workflow.id,
            node_type="trigger",
            text="Silver Touch"
        )
        db.add(nodes['silver_touch'])
        
        # Level 1 - Response nodes connected to trigger
        nodes['ahmedabad'] = Node(
            workflow_id=workflow.id,
            node_type="response",
            text="Ahmedabad"
        )
        db.add(nodes['ahmedabad'])
        
        nodes['delhi'] = Node(
            workflow_id=workflow.id,
            node_type="response",
            text="Delhi"
        )
        db.add(nodes['delhi'])
        
        nodes['canada'] = Node(
            workflow_id=workflow.id,
            node_type="response",
            text="Canada"
        )
        db.add(nodes['canada'])
        
        # Level 2 - Response nodes connected to Ahmedabad
        nodes['ai'] = Node(
            workflow_id=workflow.id,
            node_type="response",
            text="AI"
        )
        db.add(nodes['ai'])
        
        nodes['php'] = Node(
            workflow_id=workflow.id,
            node_type="response",
            text="PHP"
        )
        db.add(nodes['php'])
        
        # Level 3 - Final response
        nodes['hello_ai'] = Node(
            workflow_id=workflow.id,
            node_type="response",
            text="Hello from AI"
        )
        db.add(nodes['hello_ai'])
        
        db.commit()
        
        # Refresh all nodes to get IDs
        for node in nodes.values():
            db.refresh(node)
        
        print(f"✓ Created {len(nodes)} nodes")
        for name, node in nodes.items():
            print(f"  - {name}: '{node.text}' (ID: {node.id})")

        # 4. Create edges
        edges = [
            # Silver Touch -> Level 1
            ("silver_touch", "ahmedabad"),
            ("silver_touch", "delhi"),
            ("silver_touch", "canada"),
            
            # Ahmedabad -> Level 2
            ("ahmedabad", "ai"),
            ("ahmedabad", "php"),
            
            # AI -> Final
            ("ai", "hello_ai"),
        ]
        
        created_edges = []
        for from_name, to_name in edges:
            edge = Edge(
                workflow_id=workflow.id,
                from_node_id=nodes[from_name].id,
                to_node_id=nodes[to_name].id
            )
            db.add(edge)
            created_edges.append((from_name, to_name))
        
        db.commit()
        print(f"✓ Created {len(edges)} edges:")
        for from_name, to_name in created_edges:
            print(f"  - {nodes[from_name].text} → {nodes[to_name].text}")

        print(f"\n✅ SUCCESS! Test workflow created:")
        print(f"   Chatbot ID: {chatbot.id}")
        print(f"   Workflow ID: {workflow.id}")
        print(f"\n   Test the workflow:")
        print(f"   1. Open: http://localhost:3000/chat/{chatbot.id}")
        print(f"   2. Click 'Silver Touch' button")
        print(f"   3. You should see: Ahmedabad, Delhi, Canada")
        print(f"   4. Click 'Ahmedabad'")
        print(f"   5. You should see: AI, PHP")
        print(f"   6. Click 'AI'")
        print(f"   7. You should see: Hello from AI")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating workflow: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("Creating test workflow from image...\n")
    create_test_workflow()
