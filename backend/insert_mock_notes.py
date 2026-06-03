import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from database import queries as q
import uuid

def inject_mock_data():
    upc = "MOCK-TEST"
    print(f"Injecting highly detailed mock data for {upc}...")
    
    # 1. Paper
    q.upsert_paper(upc, {
        "paper_name": "Autonomous UI Telemetry & Design Physics",
        "department": "Computer Science",
        "programme": "B.Tech",
        "semester": "6",
        "paper_type": "Core",
        "pipeline_status": "complete"
    })
    
    # 2. Units
    u1 = q.create_unit(upc, 1, "Spatial Glass Mechanics", estimated_study_hours=4.5, marks_weightage=25)
    u2 = q.create_unit(upc, 2, "Blur-to-Focus Physics", estimated_study_hours=3.0, marks_weightage=15)
    
    q.set_unit_status(u1["id"], "complete")
    q.set_unit_status(u2["id"], "complete")
    
    q.save_unit_summary(u1["id"], {
        "what_this_unit_is_about": "This unit covers the foundational CSS and Framer Motion logic required to build lag-free, premium spatial glass interfaces.",
        "core_themes": ["CSS Radial Gradients", "Backdrop Filters", "Spring Physics"],
        "how_it_connects_to_next": "Understanding spatial glass is required before applying blur-to-focus scrolling animations in Unit 2."
    }, {
        "big_picture_takeaway": "Spatial Glass isn't just a style; it's an optimization technique that avoids WebGL overhead.",
        "real_world_applications": ["Dashboard Design", "Operating System UIs", "Premium SaaS Portals"],
        "common_exam_traps": ["Relying heavily on heavy JS animations instead of CSS transforms."]
    })
    
    # 3. Topics for Unit 1
    t1 = q.create_topic(u1["id"], upc, "Kinetic Aurora Generation", 1)
    
    mock_content = {
        "difficulty": 3,
        "estimated_study_minutes": 45,
        "priority": 1,
        "depth_signal_source": "PYQs (High Frequency)",
        "rapid_revision": "Kinetic Auroras use overlapping radial gradients with will-change: transform to achieve 60fps animations.",
        "definition": {
            "term": "Kinetic Aurora",
            "meaning": "A visual design technique utilizing multiple CSS radial gradients that slowly translate and scale to simulate the flowing motion of the Northern Lights, optimized via GPU acceleration.",
            "simplification": "Like pointing several colored flashlights at a wall and slowly moving them around, but done with CSS instead of 3D rendering."
        },
        "core_concept": {
            "explanation": "To avoid the massive performance hits of Three.js or canvas-based liquid meshes, Kinetic Auroras rely purely on CSS variables. By binding `--x` and `--y` positions to slow keyframe animations, the browser can composite the gradients entirely on the GPU. The `will-change: transform` property is critical as it forces the browser to create a separate composite layer.",
            "why_it_matters": "It allows web applications to look extremely high-end and dynamic without draining battery or causing scroll lag."
        },
        "analogy": "Imagine a theater stage with multiple colored spotlights (radial gradients) moving across the backdrop. Instead of repainting the entire stage every frame (JS rendering), we just move the lights using mechanical tracks (GPU transforms).",
        "analogy_verified": True,
        "examples": [
            {
                "scenario": "StudyAI Landing Page",
                "application": "Using three interconnected meshes (accent, primary, secondary) rotating in opposing 20s infinite loops."
            }
        ],
        "examiners_note": "Examiners frequently ask to compare CSS gradient animation performance vs Canvas API. Always highlight `will-change` and composite layers in your answer.",
        "examiners_note_pyq_refs": ["2023 Q1(a)", "2021 Q4(b)"],
        "common_mistakes": [
            {
                "mistake": "Animating background-position",
                "correction": "Never animate `background-position` as it triggers layout repaints. Always animate `transform: translate()` instead."
            }
        ],
        "answer_writing_technique": "Start with the definition, immediately state the performance benefit (60fps/GPU), and draw a quick diagram showing the overlapping layers.",
        "pyqs": [
            {
                "question": "Explain how CSS transforms provide better animation performance than animating positioning properties. (5 Marks)",
                "year_marks_source": "2022 - 5 Marks",
                "solution_strategy": "1. Explain the browser rendering pipeline (Layout -> Paint -> Composite). 2. Show how transforms skip Layout/Paint. 3. Conclude with battery/framerate implications.",
                "importance_rating": 4
            }
        ],
        "quick_checks": [
            {
                "question": "Which CSS property forces an element into its own composite layer for GPU acceleration?",
                "answer": "will-change: transform"
            },
            {
                "question": "Why is animating background-color bad for performance?",
                "answer": "It triggers paint operations on the CPU on every single frame."
            }
        ]
    }
    
    q.save_topic_content(t1["id"], mock_content)
    
    print("Mock data successfully injected! You can now view http://localhost:3000/paper/MOCK-TEST")

if __name__ == "__main__":
    inject_mock_data()
