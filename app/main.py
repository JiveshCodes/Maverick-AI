"""
app/main.py
-----------
The entry point of Maverick v0.5 (Core Brain + Voice + Memory + Web Tools + Level 5 OS Control).
Runs the interactive Command-Line Interface (CLI) loop, manages user inputs,
handles top-level errors, executes voice, memory, & OS tool commands, and displays/speaks AI responses.
"""

import sys
from app.config import Config
from app.ai import LLMBrain
from app.voice import VoiceEngine


def print_banner(voice_status: str, groq_status: str, memory_count: int, tool_count: int) -> None:
    """Prints a friendly ASCII banner and instructions when Maverick starts."""
    print("=" * 76)
    print("  🤖 MAVERICK - LEVEL 5 (v0.5) AUTONOMOUS EXECUTION & OS CONTROL")
    print("=" * 76)
    print(" Welcome, Jivesh! Maverick is running.")
    print(f" LLM Engine: Gemini Primary | Groq Backup: {groq_status}")
    print(f" Persistent Memory: ACTIVE 💾 ({memory_count} saved memories)")
    print(f" Tool Engine: ACTIVE 🛠️ ({tool_count} external & OS control tools ready)")
    print(" Commands:")
    print("   - Type your message and press Enter to talk.")
    print("   - Type '/listen' or '/mic' to speak into your microphone.")
    print(f"   - Type '/voice' to toggle spoken audio responses (Current: {voice_status}).")
    print("   - Type '/tools' to view active external tools & descriptions.")
    print("   - Type '/memory' to view stored long-term memories.")
    print("   - Type '/remember <fact>' or '/remember <key> = <value>' to save a memory.")
    print("   - Type '/forget <id or key>' or '/forget all' to remove memories.")
    print("   - Type '/history' to inspect session conversation history.")
    print("   - Type '/clear' or '/reset' to wipe session history.")
    print("   - Type 'exit' or 'quit' to close Maverick.")
    print("=" * 72)


def main() -> None:
    """Main execution loop for Maverick."""
    # Step 1: Initialize the AI Brain and Voice Engine
    try:
        print("[System] Initializing Maverick Core Brain, Voice Engine, Memory & Tools...")
        brain = LLMBrain()
        voice = VoiceEngine()
        voice_status = "ON 🔊" if voice.enabled else "OFF 🔇"
        groq_status = "ACTIVE ⚡" if brain.has_groq_backup else "INACTIVE"
        memory_count = brain.memory.get_count()
        tool_count = brain.tools.get_count()

        print_banner(voice_status, groq_status, memory_count, tool_count)
        print("[System] Ready! Type a message or enter '/listen' to speak.\n")

    except ValueError as config_err:
        # Handles missing GEMINI_API_KEY cleanly before starting the loop
        print(config_err)
        sys.exit(1)
    except Exception as err:
        print(f"\n[CRITICAL ERROR] Failed to start Maverick: {err}")
        sys.exit(1)

    # Step 2: Interactive Conversation Loop
    while True:
        try:
            # Prompt user for input
            user_input = input("You: ").strip()

            # Handle Microphone Input Command (/listen or /mic)
            if user_input.lower() in ["/listen", "/mic"]:
                speech_text = voice.listen()
                if not speech_text:
                    continue
                print(f"You (Voice): {speech_text}")
                user_input = speech_text

            # Handle Empty Input
            if not user_input:
                print("Maverick: Please enter a message! I can't respond to empty input.\n")
                continue

            # Handle Exit Commands
            if user_input.lower() in ["exit", "quit"]:
                goodbye_msg = "Shutting down Maverick... Goodbye!"
                print(f"\n[System] {goodbye_msg}")
                voice.speak(goodbye_msg)
                break

            # Handle Voice Output Toggle Command
            if user_input.lower().startswith("/voice"):
                new_state = voice.toggle_mode()
                state_str = "ENABLED 🔊" if new_state else "DISABLED 🔇"
                status_msg = f"Voice output is now {state_str}."
                print(f"\n[System] {status_msg}\n")
                if new_state:
                    voice.speak("Voice output enabled.")
                continue

            # Level 4 Tools Command: View registered external tools (/tools)
            if user_input.lower() == "/tools":
                tools_list = brain.tools.list_tools()
                print(f"\n--- 🛠️ Active External Tools ({len(tools_list)} tools) ---")
                for t in tools_list:
                    params_str = ", ".join([f"{k}: {v}" for k, v in t['parameters'].items()]) if t['parameters'] else "None"
                    print(f" • {t['name']}")
                    print(f"   Description: {t['description']}")
                    print(f"   Parameters: {params_str}")
                print("---------------------------------------------------\n")
                continue

            # Level 3 Memory Command: View stored persistent memories (/memory)
            if user_input.lower() == "/memory":
                memories = brain.memory.get_all_memories()
                print(f"\n--- 💾 Persistent Long-Term Memory ({len(memories)} entries) ---")
                if not memories:
                    print(" No saved memories found. Tell me facts or use '/remember <fact>' to add some!")
                else:
                    for item in memories:
                        print(f" [{item['id']}] [{item['category'].upper()}] {item['key']}: {item['value']}")
                print("-----------------------------------------------------------\n")
                continue

            # Level 3 Memory Command: Manually store a memory (/remember <fact> or /remember key = value)
            if user_input.lower().startswith("/remember"):
                fact_str = user_input[len("/remember"):].strip()
                if not fact_str:
                    print("Usage: /remember <fact>  OR  /remember <key> = <value>\n")
                    continue

                if "=" in fact_str:
                    parts = fact_str.split("=", 1)
                    key, val = parts[0].strip(), parts[1].strip()
                else:
                    key = "Observation"
                    val = fact_str

                brain.memory.add_memory(key=key, value=val, category="user_added")
                save_msg = f"Saved memory: '{key}: {val}'"
                print(f"\n[System 💾] {save_msg}\n")
                voice.speak("Memory saved.")
                continue

            # Level 3 Memory Command: Delete memory (/forget <id or key> or /forget all)
            if user_input.lower().startswith("/forget"):
                target = user_input[len("/forget"):].strip()
                if not target:
                    print("Usage: /forget <id_or_key>  OR  /forget all\n")
                    continue

                if target.lower() == "all":
                    removed_cnt = brain.memory.clear_all()
                    forget_msg = f"Cleared all {removed_cnt} persistent memories."
                    print(f"\n[System 💾] {forget_msg}\n")
                    voice.speak("All memories cleared.")
                else:
                    success = brain.memory.delete_memory(target)
                    if success:
                        forget_msg = f"Memory '{target}' successfully deleted."
                        print(f"\n[System 💾] {forget_msg}\n")
                        voice.speak("Memory deleted.")
                    else:
                        print(f"\n[System 💾] Could not find memory matching '{target}'. Use '/memory' to view valid IDs or keys.\n")
                continue

            # Special Command: Inspect current short-term conversation context
            if user_input.lower() == "/history":
                history = brain.get_history()
                print(f"\n--- Conversation History ({len(history)} messages) ---")
                for item in history:
                    print(f"[{item['role'].upper()}]: {item['text']}")
                print("---------------------------------------------------\n")
                continue

            # Special Command: Reset short-term conversation memory
            if user_input.lower() in ["/clear", "/reset"]:
                brain.reset()
                clear_msg = "Short-term conversation memory reset! Long-term persistent memory remains intact."
                print(f"\n[System] {clear_msg}\n")
                voice.speak("Session memory reset.")
                continue

            # Step 3: Send message to LLM and get response (triggers tools if needed)
            print("Maverick: Thinking...", end="\r")
            response = brain.send_message(user_input)

            # Clear "Thinking..." line and display response cleanly
            print(" " * 30, end="\r")
            print(f"Maverick: {response}\n")

            # Step 4: Play voice response if voice is enabled
            voice.speak(response)

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\n\n[System] Interrupted by user. Exiting Maverick...")
            break
        except Exception as e:
            # Catch API errors / network drops without crashing the whole program loop
            print(f"\n[ERROR] Could not get response: {e}")
            print("Tip: Check your internet connection or API key quota, then try again.\n")


if __name__ == "__main__":
    main()
