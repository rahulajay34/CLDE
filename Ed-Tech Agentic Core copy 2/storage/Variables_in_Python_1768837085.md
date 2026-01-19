## What You'll Learn

In this pre-read, you'll discover:

1. What a variable is and how it works in Python
2. The different data types you can store in variables
3. How to declare and assign values to variables
4. Best practices for naming and using variables effectively

## Understanding Variables in Python

### What Is a Variable?

A variable is a named storage location in your computer's memory that holds a value so you can refer to it later. That's what a variable is - a container that holds a value so you can refer to it later. In programming, variables are the building blocks that let your code keep track of information.

A variable is simply a named storage location in your computer's memory. You can think of it like a labeled box where you can put different types of information, from numbers to words to true-or-false values. The name you give the variable is how your code identifies and accesses that information.

### Why Do Variables Matter?

Variables are essential for three key reasons:

1. **Storing Data**: Variables let your program remember important information, like a user's name or the score of a game.
2. **Performing Calculations**: You can use variables to do math, like adding two numbers together or tracking how many times a loop runs.
3. **Making Decisions**: Variables store values that your code can check to determine what actions to take, such as displaying a message based on user input.

Without variables, your code would be limited to only working with static, hard-coded values. Variables give your programs flexibility and power.

### From Known to New

Let's say you want to keep track of how many cookies you've baked. You could do it the long way:

```
cookies_baked = 0
cookies_baked = cookies_baked + 1
cookies_baked = cookies_baked + 1
cookies_baked = cookies_baked + 1
```

But that's a lot of repetitive code. With a variable, you can do the same thing much more efficiently:

```
cookies_baked = 0
cookies_baked = cookies_baked + 1  # Now we have 1 cookie
cookies_baked = cookies_baked + 1  # Now we have 2 cookies
cookies_baked = cookies_baked + 1  # Now we have 3 cookies
```

The variable `cookies_baked` acts as a container that stores the current number of cookies. We can easily update and refer to this value throughout our code.

### Core Components of Variables

There are three main parts to a variable in Python:

1. **Name**: This is the label you give the variable, like `cookies_baked` or `user_score`. Variable names must follow certain rules, which we'll cover later.
2. **Value**: This is the actual data stored in the variable, such as the number `3` or the word `"chocolate chip"`.
3. **Data Type**: This specifies the kind of information the variable can hold, like a whole number, a decimal, or text. Python has several built-in data types we'll explore.

### Putting It All Together

Here's an example of using a variable in Python:

```python
# Declare a variable to store a person's name
person_name = "Alex"

# Assign a new value to the variable
person_name = "Taylor"

# Print the value stored in the variable
print(person_name)  # Output: "Taylor"
```

In this example, we first create a variable called `person_name` and give it the value `"Alex"`. We then update the variable to store the new value `"Taylor"`. Finally, we print out the current value of `person_name`, which is `"Taylor"`.

This shows how variables allow us to store and change information throughout our code.

## Practice Exercises

1. **Pattern Recognition**: Look at the following code and identify what could be improved using variables:

   ```python
   print("The temperature outside is 72 degrees Fahrenheit.")
   print("The temperature inside is 68 degrees Fahrenheit.")
   print("The difference between the two temperatures is 4 degrees Fahrenheit.")
   ```

2. **Concept Detective**: Guess the purpose of the variables in this code:

   ```python
   total_score = 0
   player_name = "Sam"
   is_logged_in = True
   ```

3. **Real-Life Application**: List 3 situations in your daily life where you could use variables to make things easier.

4. **Spot the Error**: What's wrong with the code below?

   ```python
   age = 30
   age = age + 1
   print(the_age)
   ```

5. **Planning Ahead**: How would you apply the concept of variables to keep track of inventory in a small online store?