[
  {
    "Question": "What is the primary purpose of the HTTP GET method?",
    "Options": "A) To retrieve data from a server\nB) To send data to a server\nC) To update data on a server\nD) To delete data from a server",
    "Correct Answer": "A",
    "Explanation": "The HTTP GET method is used to retrieve data from a server. It is a read-only operation that does not modify the server-side resource.",
    "Bloom's Level": "Remember"
  },
  {
    "Question": "When would you use the HTTP POST method?",
    "Options": "A) To retrieve data from a server\nB) To send new data to a server\nC) To update an existing resource on a server\nD) Both B and C",
    "Correct Answer": "D",
    "Explanation": "The HTTP POST method is used to send new data to a server or to update an existing resource on a server. It is a write operation that creates or modifies data on the server-side.",
    "Bloom's Level": "Understand"
  },
  {
    "Question": "What is the primary difference between the HTTP PUT and PATCH methods?",
    "Options": "A) PUT replaces the entire resource, PATCH updates a partial resource\nB) PUT is used for creating new resources, PATCH is used for updating existing resources\nC) PUT is a read-only operation, PATCH is a write operation\nD) There is no difference, they are used interchangeably",
    "Correct Answer": "A",
    "Explanation": "The key difference between PUT and PATCH is that PUT replaces the entire resource, while PATCH updates a partial resource. PUT is a complete replacement, while PATCH is a partial update.",
    "Bloom's Level": "Understand"
  },
  {
    "Question": "What is the purpose of the HTTP DELETE method?",
    "Options": "A) To retrieve data from a server\nB) To send data to a server\nC) To update data on a server\nD) To delete data from a server",
    "Correct Answer": "D",
    "Explanation": "The HTTP DELETE method is used to delete a resource from the server. It is a write operation that removes the specified resource from the server.",
    "Bloom's Level": "Remember"
  },
  {
    "Question": "Which of the following best describes the HTTP request/response cycle?",
    "Options": "A) The client sends a request to the server, the server processes the request and sends a response back to the client\nB) The server sends a request to the client, the client processes the request and sends a response back to the server\nC) The client and server communicate directly with each other in a continuous loop\nD) The client and server do not communicate, they operate independently",
    "Correct Answer": "A",
    "Explanation": "The HTTP request/response cycle is a fundamental concept in web development. The client (typically a web browser) sends a request to the server, and the server processes the request and sends a response back to the client.",
    "Bloom's Level": "Understand"
  },
  {
    "Question": "What is the primary benefit of using the Fetch API in JavaScript over the older XMLHttpRequest API?",
    "Options": "A) Fetch is more performant and efficient\nB) Fetch provides a more modern and intuitive syntax\nC) Fetch automatically handles CORS (Cross-Origin Resource Sharing) issues\nD) Both B and C",
    "Correct Answer": "D",
    "Explanation": "The Fetch API provides a more modern and intuitive syntax for making HTTP requests compared to the older XMLHttpRequest API. Additionally, Fetch automatically handles CORS (Cross-Origin Resource Sharing) issues, making it easier to work with APIs from different domains.",
    "Bloom's Level": "Understand"
  },
  {
    "Question": "When using the Fetch API to make a GET request, which of the following is the correct syntax?",
    "Options": "A) fetch('https://api.example.com/data')\nB) fetch('https://api.example.com/data', { method: 'GET' })\nC) fetch('https://api.example.com/data', { type: 'GET' })\nD) Both A and B",
    "Correct Answer": "D",
    "Explanation": "When making a GET request with the Fetch API, you can use either the simple form (fetch('https://api.example.com/data')) or the more explicit form (fetch('https://api.example.com/data', { method: 'GET' })).",
    "Bloom's Level": "Apply"
  },
  {
    "Question": "How do you make a POST request using the Fetch API?",
    "Options": "A) fetch('https://api.example.com/data', { method: 'POST' })\nB) fetch('https://api.example.com/data', { type: 'POST' })\nC) fetch('https://api.example.com/data', { request: 'POST' })\nD) Both A and B",
    "Correct Answer": "A",
    "Explanation": "To make a POST request with the Fetch API, you need to include the `method: 'POST'` option in the second argument of the `fetch()` function.",
    "Bloom's Level": "Apply"
  },
  {
    "Question": "What is the purpose of the `fetch()` function's second argument, the options object?",
    "Options": "A) It allows you to configure the HTTP request, such as setting the request method, headers, and request body\nB) It is used to handle the response from the server\nC) It is used to catch any errors that occur during the request\nD) Both A and B",
    "Correct Answer": "A",
    "Explanation": "The second argument of the `fetch()` function, the options object, is used to configure the HTTP request. This includes setting the request method, headers, and request body, among other options.",
    "Bloom's Level": "Understand"
  },
  {
    "Question": "Which Fetch API method is used to handle the response from the server?",
    "Options": "A) `fetch()`\nB) `then()`\nC) `catch()`\nD) `response()`",
    "Correct Answer": "B",
    "Explanation": "The `.then()` method of the Fetch API is used to handle the response from the server. It allows you to access the response data and perform further processing on it.",
    "Bloom's Level": "Apply"
  }
]