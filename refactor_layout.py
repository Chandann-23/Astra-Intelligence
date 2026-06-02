import sys
import re

file_path = "frontend/src/app/page.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the Header props in Main Chat Area
header_target = """        <Header 
          isMobileNavOpen={isMobileNavOpen}
          setIsMobileNavOpen={setIsMobileNavOpen}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          ragMode={ragMode}
          setRagMode={setRagMode}
        />"""

header_replacement = """        <Header 
          isMobileNavOpen={isMobileNavOpen}
          setIsMobileNavOpen={setIsMobileNavOpen}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          isHistoryOpen={isHistoryOpen}
          setIsHistoryOpen={setIsHistoryOpen}
          ragMode={ragMode}
          setRagMode={setRagMode}
        />"""

if header_target in content:
    content = content.replace(header_target, header_replacement)
else:
    print("Could not find Header target")
    sys.exit(1)


# 2. Swap Engine Insights and Main Chat Area
# Split by comments
sidebar_logs_start = content.find("      {/* Sidebar - Terminal Logs (25% width) */}")
main_chat_start = content.find("      {/* Main Chat Area (75% width) */}")
toast_start = content.find("      {/* Toast Notification */}")

if sidebar_logs_start == -1 or main_chat_start == -1 or toast_start == -1:
    print("Could not find layout blocks")
    sys.exit(1)

pre_logs = content[:sidebar_logs_start]
logs_block = content[sidebar_logs_start:main_chat_start]
chat_block = content[main_chat_start:toast_start]
post_toast = content[toast_start:]

# Modify the chat block class
chat_block = chat_block.replace("lg:w-[75%]", "")

# Modify logs block class (change border-r to border-l, though it's already border-l)
logs_block = logs_block.replace("border-l border-zinc-800/50 bg-zinc-950/40 backdrop-blur-xl flex-col overflow-hidden z-10", "border-l border-white/5 bg-zinc-950/80 backdrop-blur-3xl flex-col overflow-hidden z-10 flex-shrink-0")
logs_block = logs_block.replace('animate={{ width: "25%", opacity: 1 }}', 'animate={{ width: 320, opacity: 1 }}')
logs_block = logs_block.replace('Sidebar - Terminal Logs (25% width)', 'Right Sidebar - Terminal Logs (Engine Insights)')

# 3. Update the Left Sidebar (Chat History) to be toggleable
left_sidebar_target = """      {/* Left Navigation Sidebar - Gemini Style */}
      <Sidebar 
        isMobileNavOpen={isMobileNavOpen}
        setIsMobileNavOpen={setIsMobileNavOpen}
        resetChat={() => {
          setMessages([{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }]);
          setCurrentChatId(uuidv4());
          setLogs([]);
          setTopic("");
          setLoading(false);
          setIsWarmingUp(false);
          setActiveAgent(null);
        }}
        loadChat={loadChat}
        currentChatId={currentChatId}
        showToast={showToast}
        isAboutOpen={isAboutOpen}
        setIsAboutOpen={setIsAboutOpen}
      />"""

left_sidebar_replacement = """      {/* Left Navigation Sidebar - Chat History */}
      <AnimatePresence initial={false}>
        {isHistoryOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 240, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="hidden md:block h-full flex-shrink-0 overflow-hidden"
          >
            <div className="w-[240px] h-full">
              <Sidebar 
                isMobileNavOpen={false}
                setIsMobileNavOpen={setIsMobileNavOpen}
                resetChat={() => {
                  setMessages([{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }]);
                  setCurrentChatId(uuidv4());
                  setLogs([]);
                  setTopic("");
                  setLoading(false);
                  setIsWarmingUp(false);
                  setActiveAgent(null);
                }}
                loadChat={loadChat}
                currentChatId={currentChatId}
                showToast={showToast}
                isAboutOpen={isAboutOpen}
                setIsAboutOpen={setIsAboutOpen}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Mobile Sidebar */}
      <div className="md:hidden">
        <Sidebar 
          isMobileNavOpen={isMobileNavOpen}
          setIsMobileNavOpen={setIsMobileNavOpen}
          resetChat={() => {
            setMessages([{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }]);
            setCurrentChatId(uuidv4());
            setLogs([]);
            setTopic("");
            setLoading(false);
            setIsWarmingUp(false);
            setActiveAgent(null);
          }}
          loadChat={loadChat}
          currentChatId={currentChatId}
          showToast={showToast}
          isAboutOpen={isAboutOpen}
          setIsAboutOpen={setIsAboutOpen}
        />
      </div>"""

if left_sidebar_target in pre_logs:
    pre_logs = pre_logs.replace(left_sidebar_target, left_sidebar_replacement)
else:
    # try looking for it with duplicate comments
    alt_target = "      {/* Left Navigation Sidebar - Gemini Style */}\n" + left_sidebar_target
    if alt_target in pre_logs:
        pre_logs = pre_logs.replace(alt_target, left_sidebar_replacement)
    else:
        print("Could not find Left Sidebar target")
        sys.exit(1)

# Now assemble: pre_logs + chat_block + logs_block + post_toast
new_content = pre_logs + chat_block + logs_block + post_toast

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Successfully refactored layout!")
