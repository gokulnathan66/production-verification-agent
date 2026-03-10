#!/usr/bin/env python3
"""
Test script for production verification workflow
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path

INTRACT_URL = "http://localhost:8006"
ORCHESTRATOR_URL = "http://localhost:8000"


async def test_verification_flow():
    """Test the complete verification flow"""
    
    print("=" * 60)
    print("🧪 Testing Production Verification Flow")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Check app health
        print("\n1️⃣  Checking app health...")
        try:
            response = await client.get(f"{INTRACT_URL}/health")
            health = response.json()
            print(f"   ✅ Status: {health['status']}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return
        
        # 2. Check orchestrator agent health
        print("\n2️⃣  Checking orchestrator agent health...")
        try:
            response = await client.get(f"{ORCHESTRATOR_URL}/health")
            print(f"   ✅ Orchestrator agent is online")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return
        
        # 3. List artifacts
        print("\n3️⃣  Listing available artifacts...")
        try:
            response = await client.get(f"{INTRACT_URL}/api/artifacts")
            artifacts = response.json()
            
            if not artifacts['artifacts']:
                print("   ⚠️  No artifacts found. Please upload a code artifact first.")
                print("   💡 Visit http://localhost:8006 to upload")
                return
            
            print(f"   ✅ Found {len(artifacts['artifacts'])} artifact(s)")
            
            # Use first artifact
            artifact = artifacts['artifacts'][0]
            s3_key = artifact['s3_key']
            filename = artifact['filename']
            
            print(f"   📦 Using: {filename}")
            print(f"   🔑 S3 Key: {s3_key}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return
        
        # 4. Trigger verification
        print("\n4️⃣  Triggering verification workflow...")
        try:
            form_data = {
                's3_key': s3_key,
                'project_name': 'test-project',
                'metadata': json.dumps({'test': True})
            }
            
            response = await client.post(
                f"{INTRACT_URL}/api/verify/trigger",
                data=form_data
            )
            response.raise_for_status()
            result = response.json()
            
            task_id = result['task_id']
            print(f"   ✅ Verification triggered!")
            print(f"   🆔 Task ID: {task_id}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            if hasattr(e, 'response'):
                print(f"   Response: {e.response.text}")
            return
        
        # 5. Monitor task status
        print("\n5️⃣  Monitoring task status...")
        print("   (This may take a few minutes...)")
        
        max_attempts = 60
        for attempt in range(max_attempts):
            try:
                response = await client.get(
                    f"{INTRACT_URL}/api/tasks/{task_id}/details"
                )
                task = response.json()['task']
                status = task['status']
                
                print(f"   [{attempt+1}/{max_attempts}] Status: {status}")
                
                if status == 'completed':
                    print("\n   ✅ Verification completed!")
                    print(f"   📊 Result: {json.dumps(task.get('result', {}), indent=2)}")
                    break
                elif status == 'error':
                    print(f"\n   ❌ Verification failed!")
                    print(f"   Error: {task.get('error')}")
                    break
                
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"   ⚠️  Status check failed: {e}")
                await asyncio.sleep(5)
        
        print("\n" + "=" * 60)
        print("🎯 Test Complete!")
        print("=" * 60)
        print(f"\n📊 View results at: {INTRACT_URL}/tasks.html")
        print(f"📈 View progress at: {INTRACT_URL}/progress.html?task_id={task_id}")


if __name__ == "__main__":
    try:
        asyncio.run(test_verification_flow())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
