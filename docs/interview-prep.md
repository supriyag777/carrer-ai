# Presenting CareerAI in a Software Developer interview

## 30 technical questions

1. Why did you choose FastAPI for the backend?
2. How does the React client authenticate requests?
3. Why keep AI calls on the server?
4. How are passwords hashed and verified?
5. What is the responsibility of a Pydantic schema?
6. How does SQLAlchemy map the relational model?
7. Why are `role_skills` and `user_skills` separate tables?
8. How would you migrate from SQLite to MySQL safely?
9. What indexes matter for a production version?
10. How is roadmap progress calculated?
11. How would you prevent duplicate roadmap generation?
12. How does the aptitude grading flow persist answers?
13. What makes arbitrary code execution unsafe?
14. How would you isolate a Python evaluator in production?
15. How would you add test-case execution to coding submissions?
16. How are interview answers evaluated when the AI provider is unavailable?
17. What is the local AI fallback and why is it separate?
18. How do you validate AI output before rendering it?
19. How would you stream AI responses to the browser?
20. How does the dashboard aggregate scores from multiple modules?
21. What is the difference between authentication and authorization here?
22. How would you add refresh tokens or session revocation?
23. What is the purpose of CORS configuration?
24. How would you rate-limit AI endpoints?
25. How would you handle file uploads for PDF resumes?
26. How would you protect chat history from cross-user access?
27. How does the SPA fallback interact with `/api` routes?
28. What would you add to observability in production?
29. What would you test at the API boundary?
30. What are the first performance bottlenecks you would measure?

## 15 HR and project explanation questions

1. Explain CareerAI in 60 seconds.
2. What problem did you personally want to solve?
3. Who is the first user for this product?
4. Which feature would you improve first with more time?
5. Tell me about a trade-off you made.
6. How did you decide what belongs in the MVP?
7. What was the hardest technical boundary?
8. How did you keep the UI from becoming a static mockup?
9. How do you know the roadmap is useful?
10. What did you learn from connecting frontend and backend?
11. How would you explain the project to a non-technical stakeholder?
12. What would success look like after 90 days?
13. Tell me about a bug you would expect in this system.
14. Which part of the project best represents your engineering style?
15. If you restarted, what would you design differently?

## A strong interview structure

Start with the user problem: students have content but lack a clear next step. Then show the loop: profile → role comparison → roadmap → practice → AI feedback → dashboard. Name one concrete technical decision, such as keeping provider keys server-side and giving the AI adapter a deterministic fallback. Show one end-to-end flow live: log in, toggle a roadmap item, see the dashboard activity update, then ask the assistant for the next move.

Close with a thoughtful next step: production isolation for code evaluation, stronger test coverage, and a real background job for AI-heavy analysis. This signals that you understand both the working product and the engineering path beyond the demo.
