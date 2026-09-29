from __future__ import annotations

import unittest

from local_assistant.cypher_core import ModelRoles
from local_assistant.model_workflow import MAX_MODEL_STAGES, plan_model_workflow


class ModelWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.roles = ModelRoles(
            fast="fast-candidate:8b",
            deep="deep-candidate:20b",
            vision="vision-candidate:9b",
        )

    def test_ordinary_and_deep_tasks_use_one_model(self):
        ordinary = plan_model_workflow("Make a short schedule", model_roles=self.roles)
        deep = plan_model_workflow(
            "Create a detailed threat model with assumptions and uncertainty",
            model_roles=self.roles,
        )
        self.assertEqual([item.route.model for item in ordinary.stages], [self.roles.fast])
        self.assertEqual([item.route.model for item in deep.stages], [self.roles.deep])

    def test_explicit_cross_check_uses_bounded_sequential_roles(self):
        workflow = plan_model_workflow(
            "Use multiple models to analyze this plan and cross-check the result",
            model_roles=self.roles,
        )
        self.assertEqual(
            [item.route.model for item in workflow.stages],
            [self.roles.fast, self.roles.deep, self.roles.fast],
        )
        self.assertLessEqual(len(workflow.stages), MAX_MODEL_STAGES)
        self.assertTrue(workflow.sequential_models)
        self.assertTrue(workflow.parallel_tools_allowed)
        self.assertFalse(workflow.raw_reasoning_handoff)

    def test_visual_task_observes_then_synthesizes(self):
        workflow = plan_model_workflow(
            "Explain the important details in this screenshot",
            has_image=True,
            model_roles=self.roles,
        )
        self.assertEqual(
            [item.route.model for item in workflow.stages],
            [self.roles.vision, self.roles.fast],
        )
        self.assertIn("evidence_references", workflow.stages[1].consumes)

    def test_models_never_become_the_authority_source(self):
        summary = plan_model_workflow(
            "Use all three models to review this",
            model_roles=self.roles,
        ).public_summary()
        self.assertEqual(
            summary["authority_source"],
            "deterministic host policy and approved capabilities",
        )
        self.assertFalse(summary["raw_reasoning_handoff"])


if __name__ == "__main__":
    unittest.main()
