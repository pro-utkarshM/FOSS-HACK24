import subprocess
import unittest
import os
import shutil

class TestMainGo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Creating a temporary directory for test images
        cls.test_dir = "test_images_test"
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # Creating mock image files
        for i in range(5):
            with open(os.path.join(cls.test_dir, f"image{i}.png"), "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Write minimal PNG header and some data

        # Creating a subdirectory with more images for recursive testing
        cls.sub_dir = os.path.join(cls.test_dir, "subdir")
        os.makedirs(cls.sub_dir, exist_ok=True)
        for i in range(3):
            with open(os.path.join(cls.sub_dir, f"sub_image{i}.png"), "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Write minimal PNG header and some data

    @classmethod
    def tearDownClass(cls):
        # Removing the test images after tests
        shutil.rmtree(cls.test_dir)

    def run_and_capture(self, args):
        result = subprocess.run(args, capture_output=True, text=True)
        print(f"Command: {' '.join(args)}")
        print(f"Return code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return result

    def test_no_arguments(self):
        result = self.run_and_capture(["go", "run", "main.go"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Please specify a directory", result.stderr)

    def test_invalid_directory(self):
        result = self.run_and_capture(["go", "run", "main.go", "invalid_dir"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error discovering images", result.stderr)

    def test_valid_directory(self):
        result = self.run_and_capture(["go", "run", "main.go", self.test_dir])
        self.assertEqual(result.returncode, 0)
        self.assertIn("rows:", result.stdout)
        self.assertIn("columns:", result.stdout)

    def test_empty_directory(self):
        empty_dir = "empty_test_dir"
        os.makedirs(empty_dir, exist_ok=True)
        result = self.run_and_capture(["go", "run", "main.go", empty_dir])
        self.assertEqual(result.returncode, 0)
        self.assertIn("No images found", result.stdout)
        shutil.rmtree(empty_dir)

    def test_recursive_flag(self):
        result = self.run_and_capture(["go", "run", "main.go", "-r", self.test_dir])
        self.assertEqual(result.returncode, 0)
        self.assertIn("rows:", result.stdout)
        self.assertIn("columns:", result.stdout)
        self.assertIn("image0.png", result.stdout)
        self.assertIn("sub_image0.png", result.stdout)

    def test_max_images_limit(self):
        result = self.run_and_capture(["go", "run", "main.go", "-n", "2", self.test_dir])
        self.assertEqual(result.returncode, 0)
        self.assertIn("rows:", result.stdout)
        self.assertIn("columns:", result.stdout)
        self.assertEqual(result.stdout.count("data:image/png;base64"), 2)  # Ensure only 2 images are processed

    def test_handle_window_size_change(self):
        # Mock a window size change signal
        result = self.run_and_capture(["go", "run", "main.go", self.test_dir])
        self.assertEqual(result.returncode, 0)
        # Simulate window size change signal
        result = self.run_and_capture(["pkill", "-SIGWINCH", "-f", "go run main.go"])
        self.assertEqual(result.returncode, 0)
        # Check the output again
        result = self.run_and_capture(["go", "run", "main.go", self.test_dir])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Handling window size change", result.stdout)

if __name__ == "__main__":
    unittest.main()