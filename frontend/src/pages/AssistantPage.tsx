/**
 * Finance Assistant (`/assistant`, `/assistant/:threadId`; spec 011; AC-011-1, AC-011-2, AC-011-11; mock assistant.html).
 *
 * Grounded AI chat answering questions about workspace books, periods, and risk findings.
 */

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  type AssistantMessage,
  useAskQuestion,
  useCreateThread,
  useForgetMemories,
  useForgetMemory,
  useMemories,
  useMessages,
  useThreads,
} from '../entities/assistant'
import { Icon } from '../shared/ui'
import { AnswerParts } from '../widgets/assistant'


export function AssistantPage() {
  const { t } = useTranslation(['assistant', 'common'])
  const navigate = useNavigate()
  const { threadId } = useParams<{ threadId?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()

  const { data: threadsData, isLoading: loadingThreads } = useThreads()
  const createThreadMutation = useCreateThread()

  const threads = threadsData?.items ?? []
  const activeThread = threads.find((th) => th.threadId === threadId) || threads[0]
  const currentThreadId = threadId || activeThread?.threadId

  const { data: messagesData, isLoading: loadingMessages } = useMessages(currentThreadId)
  const askQuestionMutation = useAskQuestion(currentThreadId)

  const { data: memoriesData } = useMemories()
  const forgetMemoriesMutation = useForgetMemories()
  const forgetMemoryMutation = useForgetMemory()

  const memories = memoriesData?.items ?? []

  const [inputQuestion, setInputQuestion] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasHandledQueryParam = useRef(false)

  // Auto-scroll to bottom of messages
  const messages = messagesData?.items ?? []
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages.length, askQuestionMutation.isPending])

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
    if (!q || askQuestionMutation.isPending) return

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
    try {
      await askQuestionMutation.mutateAsync({ question: q })
    } catch {
      // Error handled by query state
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

            {askQuestionMutation.isPending && (
              <div className="msg-ai">
                <img className="ai-mark" src="/brand/kredibel-mark.svg" alt="" aria-hidden="true" />
                <div className="bubble">
                  <div className="row items-center gap-2">
                    <Icon name="sparkles" size="sm" className="spin" />
                    <span className="muted small">{t('assistant:composer.sending')}</span>
                  </div>
                </div>
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
              disabled={askQuestionMutation.isPending}
            />
            <button
              className="button button-primary"
              type="submit"
              aria-label={t('assistant:composer.send')}
              disabled={!inputQuestion.trim() || askQuestionMutation.isPending}
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
            {loadingThreads ? (
              <p className="muted small">{t('common:loading', { defaultValue: 'Loading...' })}</p>
            ) : threads.length === 0 ? (
              <p className="muted small">{t('assistant:noThreads')}</p>
            ) : (
              threads.map((th) => {
                const isSelected = th.threadId === currentThreadId
                return (
                  <a
                    key={th.threadId}
                    className={`link text-sm truncate ${isSelected ? 'font-semibold' : ''}`}
                    href={`/assistant/${th.threadId}`}
                    onClick={(e) => {
                      e.preventDefault()
                      handleSelectThread(th.threadId)
                    }}
                  >
                    {th.title || t('assistant:defaultThreadTitle')}
                  </a>
                )
              })
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}
