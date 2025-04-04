import os
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext
import pyperclip
import requests
import json
from dotenv import load_dotenv
import threading

# Load environment variables from .env file
load_dotenv()

class JUnitTestGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("JUnit Test Generator")
        self.root.geometry("800x600")
        self.setup_ui()
        
        # Get API key from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            messagebox.showerror("Error", "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
            self.root.destroy()
            sys.exit(1)
    
    def setup_ui(self):
        # Frame for input elements
        input_frame = tk.Frame(self.root, padx=10, pady=10)
        input_frame.pack(fill=tk.X)
        
        # Path input label and entry
        path_label = tk.Label(input_frame, text="Java File Path:")
        path_label.pack(side=tk.LEFT)
        
        self.path_entry = tk.Entry(input_frame, width=60)
        self.path_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Generate button
        self.generate_button = tk.Button(input_frame, text="Generate JUnit Tests", command=self.generate_tests)
        self.generate_button.pack(side=tk.RIGHT, padx=5)
        
        # Output area
        output_frame = tk.Frame(self.root, padx=10, pady=5)
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = tk.Label(output_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X)
        
        # Scrolled text widget for output
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=("Courier New", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Copy button
        self.copy_button = tk.Button(output_frame, text="Copy to Clipboard", command=self.copy_to_clipboard)
        self.copy_button.pack(pady=5)
        self.copy_button.config(state=tk.DISABLED)
    
    def read_java_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {str(e)}")
            return None
    
    def generate_tests(self):
        file_path = self.path_entry.get().strip()
        
        if not file_path:
            messagebox.showerror("Error", "Please provide a valid file path")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
        
        if not file_path.endswith('.java'):
            messagebox.showerror("Error", "The file must be a Java file (.java)")
            return
        
        java_code = self.read_java_file(file_path)
        if not java_code:
            return
        
        # Clear output and disable buttons
        self.output_text.delete(1.0, tk.END)
        self.generate_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
        self.status_label.config(text="Generating tests...")
        self.root.update()
        
        # Create a thread to make the API call
        thread = threading.Thread(target=self.call_openai_api, args=(java_code, file_path))
        thread.daemon = True
        thread.start()
    
    def call_openai_api(self, java_code, file_path):
        try:
            prompt = self.create_prompt(java_code)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are an expert Java developer specializing in JUnit test creation."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                response_json = response.json()
                test_code = response_json['choices'][0]['message']['content']
                
                # Extract code from markdown if present
                if "```java" in test_code:
                    test_code = test_code.split("```java")[1]
                    if "```" in test_code:
                        test_code = test_code.split("```")[0]
                
                # Update UI in the main thread
                self.root.after(0, self.update_ui_with_result, test_code.strip())
            else:
                error_message = f"API Error: {response.status_code}\n{response.text}"
                self.root.after(0, self.show_error, error_message)
                
        except Exception as e:
            self.root.after(0, self.show_error, f"Error: {str(e)}")
    
    def update_ui_with_result(self, test_code):
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, test_code)
        self.generate_button.config(state=tk.NORMAL)
        self.copy_button.config(state=tk.NORMAL)
        self.status_label.config(text="Tests generated successfully!")
    
    def show_error(self, error_message):
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, error_message)
        self.generate_button.config(state=tk.NORMAL)
        self.copy_button.config(state=tk.DISABLED)
        self.status_label.config(text="Error occurred")
    
    def copy_to_clipboard(self):
        test_code = self.output_text.get(1.0, tk.END)
        pyperclip.copy(test_code)
        self.status_label.config(text="Copied to clipboard!")
        self.root.after(2000, lambda: self.status_label.config(text="Ready"))
    
    def create_prompt(self, java_code):
        prompt = f"""
[Context]
I'm adding JUnit tests to an existing test class. I need comprehensive test methods for the following Java class.

[Reference Documentation]
Follow JUnit 5 best practices including:
- @Test, @BeforeEach, @AfterEach annotations
- Assertions from org.junit.jupiter.api.Assertions
- Mockito for dependency mocking
- Parameterized tests for multiple input combinations
- Exception testing with assertThrows()

[Specific Task]
Analyze the Java class below and generate exhaustive JUnit 5 test methods (not the entire class) that achieve maximum code coverage.

[Technical Requirements]
1. Generate ONLY the test methods (no class declaration, imports, or package statements)
2. Include test methods for ALL public methods
3. Test ALL possible execution paths through each method
4. Generate tests for the following scenarios for each method:
   - Normal/expected inputs with correct results
   - Edge cases (empty collections, null inputs, boundary values)
   - Invalid inputs that should trigger exceptions
   - All conditional branches (if/else, switch statements)
   - For methods with loops, test: empty iterations, single iteration, multiple iterations
5. For methods with dependencies:
   - Assume mocks are already properly set up in the test class
   - Set up mock behavior for different test scenarios
   - Verify mock interactions where appropriate
6. For methods with complex inputs:
   - Create parameterized tests (@ParameterizedTest) with multiple combinations
   - Test boundary conditions for numeric inputs
   - Test empty, single-element, and multi-element collections
7. Include private helper methods for test setup when needed

[Desired Output Format]
- Organize tests by method, with clear method naming: test[MethodName][Scenario]
- Include descriptive Javadoc comments for each test method explaining what is being tested
- Group related tests using nested test classes (@Nested) when appropriate
- Include appropriate assertions for each test case
- Assume all necessary imports are already present
- Format code according to standard Java conventions

[Java Class to Test]
```java
{java_code}
```

Please generate ONLY the test methods following this structure. Do not include class declaration, imports, or package statements. Assume the test class and all necessary imports already exist.
"""
        return prompt


if __name__ == "__main__":
    root = tk.Tk()
    app = JUnitTestGenerator(root)
    root.mainloop()