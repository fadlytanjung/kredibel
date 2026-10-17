/**
 * Finance Assistant (`/assistant`, `/assistant/:threadId`; spec 011; AC-011-1, AC-011-2, AC-011-11; mock assistant.html).
 *
 * Grounded AI chat answering questions about workspace books, periods, and risk findings.
 * Gemini-style conversation experience with left sidebar history, streaming animations, and interactive diagrams.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  type AssistantMessage,
  type StepEvent,
  type ToolEvent,
  streamQuestion,
  useCreateThread,
  useForgetMemories,
  useForgetMemory,
  useInfiniteThreads,
  useMemories,
  useMessages,
} from '../entities/assistant'
import { Icon } from '../shared/ui'
import { formatDate } from '../shared/lib/formatDate'
import { ActivityTrail, AnswerParts } from '../widgets/assistant'

export function AssistantPage() {
  const { t } = useTranslation(['assistant', 'common'])
  const navigate = useNavigate()
  const { threadId } = useParams<{ threadId?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  const {
    data: threadsInfiniteData,
    isLoading: loadingThreads,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useInfiniteThreads(10)
  const createThreadMutation = useCreateThread()

  const [selectedThreadId, setSelectedThreadId] = useState<string | undefined>(undefined)

  const threads = useMemo(
    () => threadsInfiniteData?.pages.flatMap((page) => page.items) ?? [],
    [threadsInfiniteData?.pages],
  )
  const activeThread = useMemo(
    () => threads.find((th) => th.threadId === (threadId || selectedThreadId)) || threads[0],
    [threads, threadId, selectedThreadId],
  )
  const currentThreadId = threadId || selectedThreadId || activeThread?.threadId

  const { data: messagesData, isLoading: loadingMessages } = useMessages(currentThreadId)

  const { data: memoriesData } = useMemories()
  const forgetMemoriesMutation = useForgetMemories()
  const forgetMemoryMutation = useForgetMemory()

  const memories = memoriesData?.items ?? []

  const [inputQuestion, setInputQuestion] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [liveSteps, setLiveSteps] = useState<StepEvent[]>([])
  const [liveTools, setLiveTools] = useState<ToolEvent[]>([])
  const [draftText, setDraftText] = useState('')
  const [streamError, setStreamError] = useState<string | null>(null)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [sessionMessagesMap, setSessionMessagesMap] = useState<Record<string, AssistantMessage[]>>({})

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasHandledQueryParam = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Combine server messages with session messages (guarantees chat bubbles never vanish)
  const serverMessages = useMemo(() => messagesData?.items ?? [], [messagesData?.items])
  const messages = useMemo(() => {
    const activeKey = currentThreadId || selectedThreadId || threadId || ''
    const activeSessionMessages = [
      ...(sessionMessagesMap[''] ?? []),
      ...(activeKey ? (sessionMessagesMap[activeKey] ?? []) : []),
    ]
    const combined = [...serverMessages]
    for (const sm of activeSessionMessages) {
      const alreadyInServer = combined.some((m) => {
        if (m.messageId === sm.messageId) return true
        if (
          sm.messageId.startsWith('user-') &&
          m.role === 'user' &&
          m.question === sm.question &&
          Math.abs(new Date(m.createdAt).getTime() - new Date(sm.createdAt).getTime()) < 60000
        ) {
          return true
        }
        if (
          sm.role === 'assistant' &&
          m.role === 'assistant' &&
          sm.answer &&
          m.answer &&
          JSON.stringify(m.answer.parts) === JSON.stringify(sm.answer.parts)
        ) {
          return true
        }
        return false
      })
      if (!alreadyInServer) {
        combined.push(sm)
      }
    }
    return combined
  }, [serverMessages, sessionMessagesMap, currentThreadId, selectedThreadId, threadId])

  // Follow the conversation: scroll to the newest message or the answer being written, never on an
  // empty thread (the welcome state stays under the page title).
  const shownMessages = useRef(0)
  useEffect(() => {
    const grew = messages.length > shownMessages.current
    shownMessages.current = messages.length
    if (grew || isStreaming) messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
  }, [messages.length, isStreaming, draftText, liveSteps.length, liveTools.length])

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  const handleSelectThread = (id: string) => {
    setMobileSidebarOpen(false)
    setSelectedThreadId(id)
    navigate(`/assistant/${id}`)
  }

  const handleNewConversation = async () => {
    setMobileSidebarOpen(false)
    try {
      const thread = await createThreadMutation.mutateAsync({
        title: t('assistant:newThreadTitle', { date: formatDate(new Date().toISOString()) }),
        scope: 'WORKSPACE',
      })
      setSelectedThreadId(thread.threadId)
      navigate(`/assistant/${thread.threadId}`)
    } catch {
      // fallback
    }
  }

  const handleSend = async (questionToSend?: string) => {
    const q = (questionToSend ?? inputQuestion).trim()
    if (!q || isStreaming) return

    let targetThreadId = currentThreadId
    if (!targetThreadId) {
      try {
        const thread = await createThreadMutation.mutateAsync({
          title: q.slice(0, 32),
          scope: 'WORKSPACE',
        })
        targetThreadId = thread.threadId
        setSelectedThreadId(targetThreadId)
        navigate(`/assistant/${targetThreadId}`)
      } catch {
        return
      }
    }

    setInputQuestion('')
    setStreamError(null)
    setIsStreaming(true)
    setLiveSteps([])
    setLiveTools([])
    setDraftText('')

    const userTempId = `user-${Date.now()}`
    const userMessage: AssistantMessage = {
      messageId: userTempId,
      role: 'user',
      question: q,
      createdAt: new Date().toISOString(),
    }
    setSessionMessagesMap((prev) => {
      const existing = prev[targetThreadId] ?? []
      return {
        ...prev,
        [targetThreadId]: [...existing, userMessage],
      }
    })

    abortControllerRef.current?.abort()
    const abortCtrl = new AbortController()
    abortControllerRef.current = abortCtrl

    try {
      await streamQuestion(
        targetThreadId,
        q,
        {
          onStep: (step) => {
            setLiveSteps((prev) => [...prev, step])
          },
          onTool: (tool) => {
            setLiveTools((prev) => [...prev, tool])
          },
          onToken: (tok) => {
            setDraftText((prev) => prev + tok)
          },
          onMessage: (msg) => {
            setSessionMessagesMap((prev) => {
              const existing = prev[targetThreadId] ?? []
              const withoutDup = existing.filter((m) => m.messageId !== msg.messageId)
              return {
                ...prev,
                [targetThreadId]: [...withoutDup, msg],
              }
            })
            void queryClient.invalidateQueries({
              queryKey: ['assistant-messages', targetThreadId],
            })
            void queryClient.invalidateQueries({
              queryKey: ['assistant-threads-infinite'],
            })
            void queryClient.invalidateQueries({
              queryKey: ['assistant-threads'],
            })
          },
          onError: (err) => {
            setStreamError(err.message)
            const fallbackText = draftText.trim()
              ? `${draftText}\n\n*(${t('assistant:errors.interrupted', { message: err.message })})*`
              : t('assistant:errors.retrieve', { message: err.message })
            const errorMsg: AssistantMessage = {
              messageId: `err-${Date.now()}`,
              role: 'assistant',
              createdAt: new Date().toISOString(),
              answer: {
                parts: [{ type: 'text', text: fallbackText }],
                citations: [],
                grounding: { verdict: 'TEMPLATE', citations: [] },
                toolsUsed: [],
              },
            }
            setSessionMessagesMap((prev) => {
              const existing = prev[targetThreadId] ?? []
              return {
                ...prev,
                [targetThreadId]: [...existing, errorMsg],
              }
            })
          },
          onDone: () => {
            setIsStreaming(false)
            setDraftText('')
            setLiveSteps([])
            setLiveTools([])
            void queryClient.invalidateQueries({
              queryKey: ['assistant-messages', targetThreadId],
            })
          },
        },
        abortCtrl.signal,
      )
    } catch (e) {
      setIsStreaming(false)
      const errMsg = e instanceof Error ? e.message : t('assistant:errors.sendFailed')
      setStreamError(errMsg)
      const errorMsg: AssistantMessage = {
        messageId: `err-${Date.now()}`,
        role: 'assistant',
        createdAt: new Date().toISOString(),
        answer: {
          parts: [{ type: 'text', text: t('assistant:errors.send', { message: errMsg }) }],
          citations: [],
          grounding: { verdict: 'TEMPLATE', citations: [] },
          toolsUsed: [],
        },
      }
      setSessionMessagesMap((prev) => {
        const existing = prev[targetThreadId] ?? []
        return {
          ...prev,
          [targetThreadId]: [...existing, errorMsg],
        }
      })
      setDraftText('')
    }
  }

  // Handle ?q=... query param from "Ask about this" buttons (AC-011-12)
  useEffect(() => {
    const initialQuery = searchParams.get('q')
    if (initialQuery && !hasHandledQueryParam.current) {
      hasHandledQueryParam.current = true
      setSearchParams({}, { replace: true })
      void handleSend(initialQuery)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const starterQuestions = [
    t('assistant:starters.unpaid'),
    t('assistant:starters.flow'),
    t('assistant:starters.clients'),
  ]

  // The welcome prompts; the same four as the mock (assistant-welcome.html).
  const welcomePrompts = [
    { title: t('assistant:welcome.prompts.flow'), question: t('assistant:starters.flow'), icon: 'bar-chart' as const },
    { title: t('assistant:welcome.prompts.unpaid'), question: t('assistant:starters.unpaid'), icon: 'file-text' as const },
    { title: t('assistant:welcome.prompts.risk'), question: t('assistant:starters.risk'), icon: 'shield-alert' as const },
    { title: t('assistant:welcome.prompts.pnl'), question: t('assistant:starters.pnl'), icon: 'table' as const },
  ]

  const threadSidebarContent = (
    <>
      <button
        type="button"
        className="button button-primary button-block"
        onClick={handleNewConversation}
        disabled={createThreadMutation.isPending}
        data-testid="new-thread"
      >
        <Icon name="plus" size="sm" />
        <span>{t('assistant:newChat')}</span>
      </button>

      {/* Conversations history list */}
      <section className="assistant-side-section" aria-labelledby="thr-h">
        <div className="spread">
          <h2 className="assistant-side-title" id="thr-h">
            {t('assistant:earlierQuestions')}
          </h2>
          <span className="badge badge-outline">{threads.length}</span>
        </div>

        {loadingThreads && threads.length === 0 ? (
          <p className="muted small">{t('common:loading', { defaultValue: 'Loading...' })}</p>
        ) : threads.length === 0 ? (
          <p className="muted small">{t('assistant:noThreads')}</p>
        ) : (
          <>
            <div className="stack gap-1">
              {threads.map((th) => {
                const isSelected = th.threadId === currentThreadId
                const dateStr = th.lastMessageAt || th.createdAt
                const formattedDate = dateStr ? formatDate(dateStr) : null
                return (
                  <Link
                    key={th.threadId}
                    to={`/assistant/${th.threadId}`}
                    onClick={(e) => {
                      e.preventDefault()
                      handleSelectThread(th.threadId)
                    }}
                    className={`assistant-thread-btn${isSelected ? ' is-active' : ''}`}
                  >
                    <span className="assistant-thread-title">{th.title || t('assistant:defaultThreadTitle')}</span>
                    {formattedDate && <span className="assistant-thread-date">{formattedDate}</span>}
                  </Link>
                )
              })}
            </div>
            {hasNextPage && (
              <button
                type="button"
                className="button button-quiet button-sm button-block"
                onClick={() => void fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? (
                  <span className="inline-flex items-center gap-1.5">
                    <Icon name="spinner" className="spin" size="sm" />
                    {t('common:loading', { defaultValue: 'Loading...' })}
                  </span>
                ) : (
                  t('assistant:loadMoreThreads')
                )}
              </button>
            )}
          </>
        )}
      </section>

      {/* Remembered Preferences */}
      <section className="panel panel-pad stack gap-2 assistant-memory" aria-labelledby="mem-h">
        <div className="spread">
          <h2 className="assistant-side-title" id="mem-h">
            {t('assistant:remembered.title')}
          </h2>
          {memories.length > 0 && (
            <button
              type="button"
              className="link-button small"
              onClick={() => forgetMemoriesMutation.mutate()}
              disabled={forgetMemoriesMutation.isPending}
            >
              {t('assistant:remembered.forgetAll')}
            </button>
          )}
        </div>
        {memories.length === 0 ? (
          <p className="muted small">{t('assistant:remembered.empty')}</p>
        ) : (
          <ul className="remembered">
            {memories.map((mem) => (
              <li key={mem.memoryId}>
                <span>{mem.fact}</span>
                <button
                  type="button"
                  className="link-button small"
                  onClick={() => forgetMemoryMutation.mutate(mem.memoryId)}
                  disabled={forgetMemoryMutation.isPending}
                >
                  {t('assistant:remembered.forget')}
                </button>
              </li>
            ))}
          </ul>
        )}
        <p className="muted small">{t('assistant:remembered.footer')}</p>
      </section>
    </>
  )

  return (
    <div className="page stack gap-4">
      {/* Page Header */}
      <div className="page-head">
        <div className="spread">
          <div className="row">
            <button
              type="button"
              className="button button-quiet button-sm assistant-history-btn"
              onClick={() => setMobileSidebarOpen(true)}
              aria-label={t('assistant:history')}
            >
              <Icon name="table" size="sm" />
              <span>{t('assistant:history')}</span>
            </button>
            <h1 className="type-title">{t('assistant:title')}</h1>
            <span className="badge badge-outline">{t('assistant:preview')}</span>
          </div>
        </div>
        <p>{t('assistant:subtitle')}</p>
      </div>

      {/* Main Gemini-style Layout */}
      <div className="assistant-page-container">
        {/* Persistent Left Rail on Desktop */}
        <aside className="assistant-sidebar assistant-sidebar-desktop" aria-label={t('assistant:recentConversations')}>
          {threadSidebarContent}
        </aside>

        {/* Mobile Slide-over Drawer for Sidebar */}
        {mobileSidebarOpen && (
          <div className="flow-sheet">
            <button
              type="button"
              className="scrim"
              aria-label={t('assistant:closeHistory')}
              onClick={() => setMobileSidebarOpen(false)}
            />
            <section className="sheet" role="dialog" aria-modal="true" aria-label={t('assistant:history')}>
              <div className="sheet-head">
                <h2 className="type-h3">{t('assistant:recentConversations')}</h2>
                <button
                  type="button"
                  className="icon-button"
                  aria-label={t('assistant:closeHistory')}
                  onClick={() => setMobileSidebarOpen(false)}
                >
                  <Icon name="x" />
                </button>
              </div>
              <div className="sheet-body stack gap-3">{threadSidebarContent}</div>
            </section>
          </div>
        )}

        {/* Main Conversation Stream */}
        <main className="assistant-main">
          <div className="chat">
            {loadingMessages && messages.length === 0 ? (
              <div className="muted p-4">{t('common:loading', { defaultValue: 'Loading messages...' })}</div>
            ) : messages.length === 0 && !isStreaming ? (
              <div className="assistant-welcome" data-testid="assistant-welcome">
                <div className="assistant-welcome-hero">
                  <img className="assistant-welcome-mark" src="/brand/kredibel-mark.svg" alt="" aria-hidden="true" />
                  <h2 className="assistant-welcome-title">
                    {t('assistant:welcome.title', { defaultValue: 'How can I help with your books today?' })}
                  </h2>
                  <p className="assistant-welcome-subtitle">
                    {t('assistant:welcome.subtitle', {
                      defaultValue:
                        'Ask anything about your cash flow, profit & loss, reconciliation, or forensic risk findings.',
                    })}
                  </p>
                </div>
                <div className="assistant-suggestion-grid">
                  {welcomePrompts.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="assistant-prompt-card"
                      onClick={() => void handleSend(p.question)}
                      data-testid={`prompt-card-${idx}`}
                    >
                      <span className="assistant-prompt-card-icon">
                        <Icon name={p.icon} size="sm" />
                      </span>
                      <span className="assistant-prompt-card-text">
                        <strong>{p.title}</strong>
                        <span>{p.question}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg: AssistantMessage) => {
                if (msg.role === 'user') {
                  return (
                    <p key={msg.messageId} className="msg-user">
                      {msg.question}
                    </p>
                  )
                }
                return (
                  <div key={msg.messageId} className="msg-ai">
                    <img className="ai-mark" src="/brand/kredibel-mark.svg" alt="" aria-hidden="true" />
                    <div className="bubble">
                      <AnswerParts answer={msg.answer} />
                      {msg.answer?.grounding?.verdict === 'AGREED' ? (
                        <span className="grounded">
                          <Icon name="shield-check" />
                          {t('assistant:messages.groundingAgreed')}
                        </span>
                      ) : (
                        <span className="why-tag wait inline-flex items-center gap-1 text-xs">
                          <Icon name="clock" size="sm" />
                          {t('assistant:messages.groundingTemplate')}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })
            )}


            {/* In-flight streaming response with ActivityTrail & typing animation */}
            {isStreaming && (
              <div className="msg-ai" data-testid="streaming-ai-message">
                <img className="ai-mark" src="/brand/kredibel-mark.svg" alt="" aria-hidden="true" />
                <div className="bubble stack gap-3">
                  <ActivityTrail steps={liveSteps} tools={liveTools} running={isStreaming} />

                  {!draftText ? (
                    <div className="thinking-dots" aria-label={t('assistant:activity.thinking')}>
                      <span />
                      <span />
                      <span />
                    </div>
                  ) : (
                    <p className="stream-draft">
                      {draftText}
                      <span className="stream-caret" aria-hidden="true" />
                    </p>
                  )}
                </div>
              </div>
            )}

            {streamError && (
              <div className="banner banner-critical text-sm">
                <Icon name="circle-alert" size="sm" />
                <span>{streamError}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested starter questions */}
          <div className="suggested" aria-label={t('assistant:suggestedQuestions')}>
            {starterQuestions.map((q, idx) => (
              <a
                key={idx}
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  void handleSend(q)
                }}
              >
                {q}
              </a>
            ))}
          </div>

          {/* Composer */}
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault()
              void handleSend()
            }}
          >
            <input
              type="text"
              aria-label={t('assistant:composer.placeholder')}
              placeholder={t('assistant:composer.placeholder')}
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              disabled={isStreaming}
            />
            <button
              className="button button-primary"
              type="submit"
              aria-label={t('assistant:composer.send')}
              disabled={!inputQuestion.trim() || isStreaming}
            >
              <Icon name="send" size="sm" />
            </button>
          </form>
        </main>
      </div>
    </div>
  )
}
