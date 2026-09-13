# Rate Limit Exceeded

⚠️ **Whoa there!** You've hit our rate limit.

It looks like you may have sent a few too many requests. Our API implements a rolling window rate limit of 100 requests per minute per account, which helps ensure fair access and consistent performance for all of our users.

**What happened?** Your account exceeded the allowed request volume within the current window.

**What should you do?** Don't worry — this is easily resolved! Simply check the `Retry-After` header in this response, wait the specified number of seconds, and then feel free to try your request again. You may also want to consider implementing exponential backoff in your client, which is generally considered a best practice for robust API integrations.

Need a higher limit? Reach out to our team and we'd be happy to discuss options that might work better for your use case.
