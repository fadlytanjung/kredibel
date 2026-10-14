/**
 * Finance Assistant (`/assistant`, `/assistant/:threadId`; spec 011; AC-011-1, AC-011-2, AC-011-11; mock assistant.html).
 *
 * Grounded AI chat answering questions about workspace books, periods, and risk findings.
 */

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
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

  const threads = threadsInfiniteData?.pages.flatMap((page) => page.items) ?? []
  const activeThread = threads.find((th) => th.threadId === threadId) || threads[0]
  const currentThreadId = threadId || activeThread?.threadId

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
  const [optimisticUserQuestion, setOptimisticUserQuestion] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasHandledQueryParam = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Auto-scroll to bottom of messages
  const messages = messagesData?.items ?? []
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages.length, isStreaming, draftText, liveSteps.length, liveTools.length])

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  const handleSelectThread = (id: string) => {
    navigate(`/assistant/${id}`)
  }

  const handleNewConversation = async () => {
    try {
      const thread = await createThreadMutation.mutateAsync({
        title: `Question ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
        scope: 'WORKSPACE',
      })
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
        navigate(`/assistant/${targetThreadId}`)
      } catch {
        return
      }
    }

    setInputQuestion('')
    setStreamError(null)
    setOptimisticUserQuestion(q)
    setIsStreaming(true)
    setLiveSteps([])
    setLiveTools([])
    setDraftText('')

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
          onMessage: () => {
            void queryClient.invalidateQueries({
              queryKey: ['assistant', 'threads', targetThreadId, 'messages'],
            })
          },
          onError: (err) => {
            setStreamError(err.message)
          },
          onDone: () => {
            setIsStreaming(false)
            setOptimisticUserQuestion(null)
            setDraftText('')
            setLiveSteps([])
            setLiveTools([])
          },
        },
        abortCtrl.signal,
      )
    } catch (e) {
      setIsStreaming(false)
      setOptimisticUserQuestion(null)
      setDraftText('')
      setStreamError(e instanceof Error ? e.message : 'Failed to send message')
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
    t('assistant:starters.q2'),
    t('assistant:starters.clients'),
  ]

  return (
    <div className="page">
      {/* Page Header */}
      <div className="page-head">
        <div className="spread">
          <h1 className="type-title">{t('assistant:title')}</h1>
          <span className="badge badge-outline">{t('assistant:preview')}</span>
        </div>
        <p>{t('assistant:subtitle')}</p>
      </div>

      {/* Chat Layout */}
      <div className="chat-layout">
        <div className="stack gap-5">
          {/* Messages list */}
          <div className="chat">
            {loadingMessages && messages.length === 0 ? (
              <div className="muted p-4">{t('common:loading', { defaultValue: 'Loading messages...' })}</div>
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

            {/* Optimistic user question while streaming */}
            {isStreaming && optimisticUserQuestion && (
              <p className="msg-user" data-testid="optimistic-user-message">
                {optimisticUserQuestion}
              </p>
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
                    <p className="m-0 leading-relaxed whitespace-pre-line">
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

          {/* Suggested questions */}
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
              className="flex-1 min-h-10 border-0 bg-transparent text-ink placeholder:text-muted outline-none text-base px-0"
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
        </div>

        {/* Aside: Remembered Preferences & Earlier Questions */}
        <aside className="chat-aside stack gap-4">
          {/* Remembered panel */}
          <section className="panel panel-pad stack gap-3" aria-labelledby="mem-h">
            <div className="spread">
              <h2 className="type-h3" id="mem-h">
                {t('assistant:remembered.title')}
              </h2>
              {memories.length > 0 && (
                <button
                  type="button"
                  className="link small border-0 bg-transparent cursor-pointer p-0"
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
              <ul className="remembered m-0 p-0 list-none">
                {memories.map((mem) => (
                  <li key={mem.memoryId}>
                    <span>{mem.fact}</span>
                    <button
                      type="button"
                      className="link small border-0 bg-transparent cursor-pointer p-0"
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

          {/* Earlier questions panel */}
          <section className="panel panel-pad stack gap-2" aria-labelledby="thr-h">
            <div className="spread">
              <h2 className="type-h3" id="thr-h">
                {t('assistant:earlierQuestions')}
              </h2>
              <button
                type="button"
                className="link small border-0 bg-transparent cursor-pointer p-0"
                onClick={handleNewConversation}
                disabled={createThreadMutation.isPending}
              >
                + {t('assistant:newThread')}
              </button>
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
                      <a
                        key={th.threadId}
                        className={`link text-sm truncate flex items-center justify-between py-1 ${isSelected ? 'font-semibold' : ''}`}
                        href={`/assistant/${th.threadId}`}
                        onClick={(e) => {
                          e.preventDefault()
                          handleSelectThread(th.threadId)
                        }}
                      >
                        <span className="truncate">{th.title || t('assistant:defaultThreadTitle')}</span>
                        {formattedDate && (
                          <span className="text-xs muted shrink-0 ml-2">{formattedDate}</span>
                        )}
                      </a>
                    )
                  })}
                </div>
                {hasNextPage && (
                  <button
                    type="button"
                    className="button button-quiet button-sm w-full mt-2"
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
        </aside>
      </div>
    </div>
  )
}
