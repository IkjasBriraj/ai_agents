import sys
import os
import unittest

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.task_graph import TaskGraph, create_software_development_dag

class TestTaskGraph(unittest.TestCase):
    def setUp(self):
        self.graph = TaskGraph()
        self.graph.add_task("t1", "Task 1", "analysis", "Do t1")
        self.graph.add_task("t2", "Task 2", "code", "Do t2", depends_on=["t1"])

    def test_adding_tasks_and_dependency_checking(self):
        t1 = self.graph.get_task("t1")
        t2 = self.graph.get_task("t2")
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)
        self.assertEqual(t2.depends_on, ["t1"])

    def test_executable_task_detection(self):
        exec_tasks = self.graph.get_executable_tasks()
        self.assertEqual(len(exec_tasks), 1)
        self.assertEqual(exec_tasks[0].id, "t1")

        self.graph.mark_completed("t1", "t1 result")
        
        exec_tasks = self.graph.get_executable_tasks()
        self.assertEqual(len(exec_tasks), 1)
        self.assertEqual(exec_tasks[0].id, "t2")

    def test_software_development_dag(self):
        dag = create_software_development_dag("TestProject", "Test requirements")
        self.assertIsNotNone(dag.get_task("arch"))
        self.assertIsNotNone(dag.get_task("code"))
        self.assertIsNotNone(dag.get_task("qa"))
        self.assertEqual(dag.get_task("code").depends_on, ["arch"])
        self.assertEqual(dag.get_task("qa").depends_on, ["code"])

    def test_format_summary(self):
        self.graph.mark_completed("t1", "Done t1")
        self.graph.mark_failed("t2", "Failed t2")
        summary = self.graph.format_summary()
        self.assertIn("Task Graph Summary:", summary)
        self.assertIn("[COMPLETED] t1 (Task 1)", summary)
        self.assertIn("Result: Done t1", summary)
        self.assertIn("[FAILED] t2 (Task 2)", summary)
        self.assertIn("Error: Failed t2", summary)

if __name__ == '__main__':
    unittest.main()
