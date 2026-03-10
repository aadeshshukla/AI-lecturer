"""Gemini 2.5 Flash autonomous orchestrator placeholder.

TODO PR2: Implement the full Gemini orchestrator loop:
  - Configure google.generativeai with GOOGLE_API_KEY
  - Initialise GenerativeModel with function_declarations from mcp_server
  - Start continuous autonomous lecture loop:
      * Build context message from class status + pending events
      * Call chat.send_message()
      * Parse response.parts for function_call objects
      * Execute tools via mcp_server.execute_tool()
      * Feed function_response back to Gemini
      * Respect QuotaManager daily limit (250 req/day free tier)
  - Handle graceful shutdown on end_lecture() tool call
"""
