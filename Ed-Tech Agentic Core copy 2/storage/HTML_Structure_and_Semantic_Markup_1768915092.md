# HTML Structure and Semantic Markup

## Learning Objectives

By the end of this lesson, you'll be able to:

- Construct a complete HTML5 document skeleton with proper DOCTYPE, head, and body elements
- Identify when to use semantic tags like `<article>` vs `<section>` in real webpage layouts
- Create functional forms with various input types that collect user data effectively
- Choose the right HTML elements for accessibility and search engine optimization

## What Is HTML Structure and Semantic Markup?

HTML functions like the skeleton of a building. You wouldn't pile bricks randomly—you'd create a foundation, frame walls, add a roof, and designate rooms for specific purposes. HTML works the same way.

**HTML structure** organizes your web page into a logical hierarchy, while **semantic markup** uses tags that describe what content actually *is*, not just how it looks.

**HTML structure** is the skeleton that organizes your web page into a logical hierarchy, while **semantic markup** uses tags that describe what content actually *is*, not just how it looks.

## Why Structure and Semantics Matter

Without proper structure, your webpage becomes a jumbled mess—like a newspaper with no headlines, where every paragraph looks equally important. Browsers might display it, but screen readers won't know how to navigate it. Search engines won't understand what's important. Other developers won't be able to maintain your code.

Consider a real scenario: A visually impaired user visits your site with a screen reader. If you've used `<div>` tags for everything, the screen reader just announces "content, content, content." But with semantic tags like `<nav>`, `<article>`, and `<footer>`, it announces "navigation region" and lets users jump directly to main content. That's the difference between frustration and usability.

For SEO, Google's crawler sees `<nav>` and knows these are site-wide links, not main content—helping it index your pages correctly and potentially improving your search ranking.

## The HTML Document Structure

Every HTML document follows a standard skeleton:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Page Title</title>
</head>
<body>
    <!-- Your content goes here -->
</body>
</html>
```

**`<!DOCTYPE html>`** tells the browser this is an HTML5 document. Without it, browsers enter "quirks mode" and render pages inconsistently. Always put this first.

**`<html lang="en">`** wraps everything. The `lang` attribute helps screen readers pronounce words correctly and helps search engines serve your content to the right audience.

**`<head>`** contains metadata—information about your page that doesn't display on screen. The character encoding (`UTF-8`) ensures special characters display correctly. The viewport meta tag ensures your site displays properly on mobile devices by controlling how the page scales to fit different screen sizes. The `<title>` appears in browser tabs and search results.

**`<body>`** holds all visible content. Everything users see goes here.

A common mistake is putting visible content in the `<head>` or forgetting the DOCTYPE. Browsers will try to fix these errors, but you'll get unpredictable results.

## Semantic HTML Tags

Semantic tags describe content purpose, not appearance. Compare these two approaches:

**Non-semantic approach:**
```html
<div id="header">
    <div id="nav">
        <a href="/">Home</a>
    </div>
</div>
<div id="main">
    <div class="post">
        <h2>Article Title</h2>
        <p>Content here...</p>
    </div>
</div>
<div id="footer">
    <p>Copyright 2024</p>
</div>
```

**Semantic approach:**
```html
<header>
    <nav>
        <a href="/">Home</a>
    </nav>
</header>
<main>
    <article>
        <h2>Article Title</h2>
        <p>Content here...</p>
    </article>
</main>
<footer>
    <p>Copyright 2024</p>
</footer>
```

Both might look identical on screen, but using semantic tags communicates meaning to browsers, assistive technologies, and other developers.

**`<header>`** marks introductory content or navigation. You can use it for the page header or within an article for the article's header.

**`<nav>`** defines navigation links. Screen readers can jump directly to navigation, and you can have multiple nav sections (main menu, sidebar menu, footer links).

**`<main>`** wraps the primary content. Use only one per page. This tells assistive technologies where the actual content starts, letting users skip repetitive headers and navigation.

**`<article>`** represents self-contained content that could stand alone—blog posts, news articles, forum posts, product cards. If you could syndicate it to another site and it would make sense, it's an article.

**`<section>`** groups related content with a heading. Use it to break up long articles or group thematic content on a page.

**`<aside>`** marks tangentially related content—sidebars, pull quotes, related links. It's supplementary, not essential to understanding the main content.

**`<footer>`** contains closing information—copyright, contact info, related links. Like header, you can use it for the page footer or within articles.

Here's a complete example showing how these work together:

```html
<body>
    <header>
        <h1>Tech Blog</h1>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
    </header>
    
    <main>
        <article>
            <header>
                <h2>Understanding Semantic HTML</h2>
                <p>Published: <time datetime="2024-01-15">January 15, 2024</time></p>
            </header>
            
            <section>
                <h3>Why Semantics Matter</h3>
                <p>Semantic HTML improves accessibility and SEO...</p>
            </section>
            
            <aside>
                <h4>Related Reading</h4>
                <ul>
                    <li><a href="/css">CSS Basics</a></li>
                </ul>
            </aside>
        </article>
    </main>
    
    <footer>
        <p>&copy; 2024 Tech Blog</p>
    </footer>
</body>
```

Notice the **`<time>`** tag with a `datetime` attribute. This makes dates machine-readable for search engines and calendar applications while displaying human-friendly text.

A common mistake is using semantic tags just for styling. If you need a container for CSS styling without semantic meaning, use `<div>` or `<span>`. Don't abuse semantic tags as generic containers.

## Forms and Input Elements

Forms collect user data—logins, searches, surveys, checkouts. They're interactive bridges between users and your application.

Here's a basic form structure:

```html
<form action="/submit" method="POST">
    <label for="username">Username:</label>
    <input type="text" id="username" name="username" required>
    
    <label for="email">Email:</label>
    <input type="email" id="email" name="email" required>
    
    <button type="submit">Sign Up</button>
</form>
```

**`<form>`** wraps all form controls. The `action` attribute specifies where to send data. The `method` attribute determines how—`GET` adds data to the URL (good for searches you can bookmark), `POST` sends it in the request body (necessary for passwords and sensitive data that shouldn't appear in URLs).

**`<label>`** describes what each input field collects. The `for` attribute must match the input's `id`. This creates an association—clicking the label focuses the input, and screen readers announce the label when users reach the field.

**`<input>`** creates form controls. The `type` attribute determines what kind of data to collect. The `name` attribute is the key when sending data to the server. The `id` connects to the label.

### Input Types

Different input types handle different kinds of data:

```html
<form>
    <!-- Text input for short, single-line text -->
    <label for="name">Name:</label>
    <input type="text" id="name" name="name">
    
    <!-- Email input validates email format -->
    <label for="email">Email:</label>
    <input type="email" id="email" name="email">
    
    <!-- Password input hides characters -->
    <label for="password">Password:</label>
    <input type="password" id="password" name="password">
    
    <!-- Number input with min/max constraints -->
    <label for="age">Age:</label>
    <input type="number" id="age" name="age" min="0" max="120">
    
    <!-- Date picker -->
    <label for="birthday">Birthday:</label>
    <input type="date" id="birthday" name="birthday">
    
    <!-- Checkbox for yes/no options -->
    <input type="checkbox" id="subscribe" name="subscribe">
    <label for="subscribe">Subscribe to newsletter</label>
    
    <!-- Radio buttons for one choice from multiple options -->
    <input type="radio" id="size-s" name="size" value="small">
    <label for="size-s">Small</label>
    
    <input type="radio" id="size-m" name="size" value="medium">
    <label for="size-m">Medium</label>
    
    <input type="radio" id="size-l" name="size" value="large">
    <label for="size-l">Large</label>
</form>
```

Notice how radio buttons share the same `name` attribute but have unique `id` values. This groups them—users can only select one radio button per group. Each needs its own label.

**`<textarea>`** handles multi-line text:

```html
<label for="message">Message:</label>
<textarea id="message" name="message" rows="4" cols="50"></textarea>
```

**`<select>`** creates dropdown menus:

```html
<label for="country">Country:</label>
<select id="country" name="country">
    <option value="">-- Choose a country --</option>
    <option value="us">United States</option>
    <option value="ca">Canada</option>
    <option value="mx">Mexico</option>
</select>
```

The first option with an empty value serves as a placeholder. The `value` attribute is what gets sent to the server, while the text between tags is what users see.

### Complete Form Example

Here's a registration form with multiple input types:

```html
<form action="/register" method="POST">
    <h2>Create Account</h2>
    
    <label for="username">Username:</label>
    <input type="text" id="username" name="username" required minlength="3">
    
    <label for="email">Email:</label>
    <input type="email" id="email" name="email" required>
    
    <label for="password">Password:</label>
    <input type="password" id="password" name="password" required minlength="8">
    
    <label for="country">Country:</label>
    <select id="country" name="country" required>
        <option value="">-- Select --</option>
        <option value="us">United States</option>
        <option value="ca">Canada</option>
    </select>
    
    <input type="checkbox" id="terms" name="terms" required>
    <label for="terms">I agree to the terms</label>
    
    <button type="submit">Register</button>
</form>
```

The `required` attribute makes fields mandatory—browsers won't submit the form until users fill them. The `minlength` attribute sets minimum character requirements.

Common mistakes include forgetting to connect labels to inputs (always use matching `for` and `id` attributes) and using placeholder text instead of labels. Placeholders disappear when users type, causing confusion.

## Understanding Key Distinctions

**`<section>` vs `<article>`**: An article is complete on its own (a blog post), while a section is a thematic grouping within something larger (chapters in a book). You can have sections within articles, but not typically the reverse.

**`name` vs `id` in forms**: The `id` is for HTML (connecting labels, CSS styling, JavaScript). The `name` is for the server—it's the key in the data you send. You need both for accessible, functional forms.

**When to use `<div>` and `<span>`**: These are non-semantic containers. Use them only when no semantic tag fits. Overusing divs makes your HTML a "div soup" that's hard to maintain and inaccessible.

## Key Takeaways

- HTML structure follows a hierarchy: DOCTYPE, html, head, and body create the foundation for every page
- Semantic tags like `<header>`, `<nav>`, `<main>`, `<article>`, and `<footer>` describe content meaning, improving accessibility and SEO
- Forms collect user data through inputs, labels, and buttons—always connect labels to inputs with matching `for` and `id` attributes
- Different input types (`text`, `email`, `password`, `checkbox`, `radio`) provide appropriate controls and built-in validation
- HTML is the skeleton: it provides structure and meaning, while CSS handles appearance

The semantic choices you make now create a foundation for styling with CSS and adding interactivity with JavaScript. Well-structured HTML is like a well-organized closet—everything has its place, making it easy to find and modify what you need.