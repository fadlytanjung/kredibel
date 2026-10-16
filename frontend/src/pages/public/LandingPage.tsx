import { Fragment, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'
import { useScrollProgress } from '../../shared/lib/useScrollProgress'
import {
  DuplicateDecision,
  FindingMoment,
  Icon,
  PageMeta,
  ReadTwiceScene,
  ReadingsPair,
  StatementSheet,
  type IconName,
} from '../../shared/ui'
import { DepthStage } from '../../widgets/public/DepthStage'
import { FlowRibbon } from '../../widgets/public/FlowRibbon'
import { Lamp } from '../../widgets/public/Lamp'
import { PaperArtefact } from '../../widgets/public/PaperArtefact'
import { Reveal } from '../../widgets/public/Reveal'
import { ScrollStory } from '../../widgets/public/ScrollStory'
import { PublicShell } from '../../widgets/PublicShell'
import { ReadingRoomStage } from './ReadingRoomStage'

const TRUST_TICKS = ['trustCloud', 'trustNoCard', 'trustLanguages'] as const
const PROBLEMS = ['problem1', 'problem2', 'problem3'] as const
const SOLUTIONS = ['solution1', 'solution2', 'solution3'] as const
const CLOUD_ITEMS = ['item1', 'item2', 'item3', 'item4'] as const
const TRUST_ITEMS = ['item1', 'item2', 'item3', 'item4', 'item5'] as const

const CLOUD_STACK: readonly { key: string; icon: IconName }[] = [
  { key: 'svc1', icon: 'cpu' },
  { key: 'svc2', icon: 'sparkles' },
  { key: 'svc3', icon: 'scan' },
  { key: 'svc4', icon: 'layers' },
  { key: 'svc5', icon: 'folder' },
  { key: 'svc6', icon: 'lock' },
]
// The stack is drawn bottom-up, so the first service sits on top.
const PLATES = [...CLOUD_STACK].reverse()

// The dashboard leads (the section is "where the money went"); the month, review and evidence follow.
const SCREENS = [
  { src: '/marketing/dashboard.png', caption: 'landing.flow.shotCaption' },
  { src: '/marketing/month.png', caption: 'landing.howVisual.caption' },
  { src: '/marketing/review.png', caption: 'landing.review.shotCaption' },
  { src: '/marketing/evidence-viewer.png', caption: 'how.shotEvidence' },
] as const

/**
 * The public landing (spec 020, AC-020-1…4, 12; docs/12 §12): "the ledger in depth". An ink hero where
 * two readings converge on one printed figure inside a 3D deck of paper; the reading room, a scroll
 * story of what happens to every document; the live duplicate decision; why, the Google Cloud stack,
 * the real screens, the trust rules, plans and questions, and a closing call to action.
 */
export function LandingPage() {
  const { t } = useTranslation('public')

  const statementRows = [
    {
      date: t('landing.row1Date'),
      text: t('landing.row1Text'),
      amount: t('landing.row1Amount'),
      reading: 'AGREED' as const,
    },
    {
      date: t('landing.row2Date'),
      text: t('landing.row2Text'),
      amount: t('landing.row2Amount'),
      reading: 'AGREED' as const,
    },
    { date: t('landing.row3Date'), text: t('landing.row3Text'), held: true },
  ]

  const chapters = [
    { key: 'order', title: t('landing.story.c1Title'), body: t('landing.story.c1Body') },
    {
      key: 'twice',
      title: t('landing.story.c2Title'),
      body: t('landing.story.c2Body'),
      extra: (
        <ReadingsPair
          caption={t('landing.readingsCaption')}
          headers={{
            field: t('landing.readingsField'),
            ai: t('landing.readTwiceAi'),
            witness: t('landing.readTwiceWitness'),
            result: t('landing.readingsResult'),
          }}
          rows={[
            {
              label: t('landing.row1Text'),
              aiReader: t('landing.row1Amount'),
              witness: t('landing.row1Amount'),
              result: t('landing.readingsAgreed'),
              agreed: true,
            },
          ]}
        />
      ),
    },
    {
      key: 'forensics',
      title: t('landing.story.c3Title'),
      body: t('landing.story.c3Body'),
      extra: (
        <FindingMoment
          severityLabel={t('landing.risk.criticalLabel')}
          code="A01"
          title={t('landing.risk.findingTitle')}
          consequence={t('landing.risk.findingConsequence')}
          calc={{
            prevLabel: t('landing.risk.calcPrev'),
            prev: '86,420,000',
            amountLabel: t('landing.risk.calcAmount'),
            amount: '32,100,000',
            expectedLabel: t('landing.risk.calcExpected'),
            expected: '118,520,000',
            shownLabel: t('landing.risk.calcShown'),
            shown: '124,520,000',
            headers: {
              op: t('landing.risk.calcHeadOp'),
              line: t('landing.risk.calcHeadLine'),
              amount: t('landing.risk.calcHeadAmount'),
            },
          }}
          nextLabel={t('landing.risk.nextLabel')}
          nextStep={t('landing.risk.findingNext')}
        />
      ),
    },
    {
      key: 'reconciled',
      title: t('landing.story.c4Title'),
      body: t('landing.story.c4Body'),
      extra: (
        <FlowRibbon
          legend={{
            in: t('landing.story.flowIn'),
            out: t('landing.story.flowOut'),
            flagged: t('landing.story.flowFlag'),
          }}
        />
      ),
    },
  ]

  return (
    <PublicShell>
      <PageMeta title={t('meta.homeTitle')} description={t('meta.homeDescription')} path="/" />

      <Lamp className="pub-hero">
        <div className="pub-hero-inner">
          <div className="pub-hero-copy">
            <p className="pub-eyebrow">{t('landing.eyebrow')}</p>
            <h1 className="pub-hero-title">
              {t('landing.title')
                .split(' ')
                .map((word, i) => (
                  <Fragment key={`${word}-${i}`}>
                    {i > 0 && ' '}
                    <span className="w">{word}</span>
                  </Fragment>
                ))}
            </h1>
            <p className="pub-hero-lead">{t('landing.lead')}</p>
            <div className="pub-actions">
              <Link className="button button-accent button-lg pub-cta" to="/login">
                {t('landing.startTrial')}
              </Link>
              <Link className="button button-lg pub-ghost" to="/how-it-works">
                {t('landing.seeHow')}
              </Link>
            </div>
            <ul className="pub-hero-trust">
              {TRUST_TICKS.map((key) => (
                <li key={key}>
                  <Icon name="check" size="sm" />
                  {t(`landing.${key}`)}
                </li>
              ))}
            </ul>
          </div>
          <div className="pub-hero-scene">
            <DepthStage deck={['ledger', 'invoice', 'receipt', 'statement', 'receipt']}>
              <div className="pub-hero-sheet">
                <StatementSheet
                  bank={t('landing.statementBank')}
                  meta={t('landing.statementMeta')}
                  rows={statementRows}
                  balanceLabel={t('landing.balanceLabel')}
                  balance={t('landing.balanceAmount')}
                  heldLabel={t('landing.held')}
                >
                  <ReadTwiceScene
                    figure={t('landing.row1Amount')}
                    aiLabel={t('landing.readTwiceAi')}
                    witnessLabel={t('landing.readTwiceWitness')}
                    caption={t('landing.readTwiceCaption')}
                    resultLabel={t('landing.readTwiceCaption')}
                  />
                </StatementSheet>
              </div>
            </DepthStage>
          </div>
        </div>
        <span className="pub-scroll-cue" aria-hidden="true" />
      </Lamp>

      <ScrollStory
        eyebrow={t('landing.story.eyebrow')}
        title={t('landing.story.title')}
        lead={t('landing.story.lead')}
        chapters={chapters}
        stage={<ReadingRoomStage />}
      />

      <Lamp className="pub-section pub-held">
        <div className="pub-inner pub-held-grid">
          <div className="pub-held-copy">
            <Reveal className="pub-head">
              <p className="pub-eyebrow">{t('landing.review.eyebrow')}</p>
              <h2 className="pub-h2">{t('landing.review.title')}</h2>
              <p className="pub-lead">{t('landing.review.lead')}</p>
            </Reveal>
            <DuplicateDecision
              title={t('landing.decisionTitle')}
              body={t('landing.decisionBody')}
              sameLabel={t('landing.decisionSame')}
              differentLabel={t('landing.decisionDifferent')}
              sameResult={t('landing.decisionSameResult')}
              differentResult={t('landing.decisionDifferentResult')}
              totalLabel={t('landing.decisionTotal')}
              baseTotal={t('landing.decisionBaseTotal')}
              countedTotal={t('landing.decisionCountedTotal')}
            />
          </div>
          <div className="pub-held-scene" aria-hidden="true">
            <DepthStage>
              <PaperArtefact kind="statement" className="pub-held-original" />
              <PaperArtefact kind="statement" className="pub-held-dupe" stamp="held" />
            </DepthStage>
          </div>
        </div>
      </Lamp>

      <WhySection />
      <CloudSection />
      <ScreensSection />

      <Lamp className="pub-section">
        <div className="pub-inner">
          <Reveal className="pub-head">
            <p className="pub-eyebrow">{t('landing.trust.eyebrow')}</p>
            <h2 className="pub-h2">{t('landing.trust.title')}</h2>
            <p className="pub-lead">{t('landing.trust.lead')}</p>
          </Reveal>
          <TrustRules />
        </div>
      </Lamp>

      <section className="pub-section pub-paper is-sheet">
        <div className="pub-inner pub-band">
          <Link className="pub-band-card" to="/pricing">
            <p className="pub-eyebrow">{t('landing.pricingTeaser.eyebrow')}</p>
            <h2 className="pub-h3">{t('landing.pricingTeaser.title')}</h2>
            <p>{t('landing.pricingTeaser.lead')}</p>
            <span className="pub-band-go">{t('landing.pricingTeaser.cta')}</span>
          </Link>
          <Link className="pub-band-card" to="/faq">
            <p className="pub-eyebrow">{t('landing.faqTeaser.eyebrow')}</p>
            <h2 className="pub-h3">{t('landing.faqTeaser.title')}</h2>
            <p>{t('landing.faqTeaser.lead')}</p>
            <span className="pub-band-go">{t('landing.faqTeaser.cta')}</span>
          </Link>
        </div>
      </section>

      <Lamp className="pub-section pub-portal is-sheet" reveal>
        <div className="pub-inner">
          <span className="pub-portal-rule" aria-hidden="true" />
          <h2 className="pub-portal-title">{t('landing.cta.title')}</h2>
          <p className="pub-lead">{t('landing.cta.lead')}</p>
          <div className="pub-actions">
            <Link className="button button-accent button-lg pub-cta" to="/login">
              {t('landing.cta.primary')}
            </Link>
            <Link className="button button-lg pub-ghost" to="/how-it-works">
              {t('landing.cta.secondary')}
            </Link>
          </div>
        </div>
      </Lamp>
    </PublicShell>
  )
}

/** Why Kredibel: the problem recedes into the page, the answer comes forward. */
function WhySection() {
  const { t } = useTranslation('public')
  const versusRef = useRef<HTMLDivElement>(null)
  const versusView = useInViewAttr(versusRef)

  return (
    <section className="pub-section pub-paper is-sheet">
      <div className="pub-inner">
        <Reveal className="pub-head">
          <p className="pub-eyebrow">{t('landing.problem.eyebrow')}</p>
          <h2 className="pub-h2">{t('landing.problem.title')}</h2>
          <p className="pub-lead">{t('landing.problem.lead')}</p>
        </Reveal>
        <div ref={versusRef} className="pub-versus" {...versusView}>
          <div className="pub-versus-card is-problem">
            <h3>{t('landing.problem.problemTitle')}</h3>
            <ul>
              {PROBLEMS.map((key) => (
                <li key={key}>
                  <Icon name="circle-alert" size="sm" />
                  <span>{t(`landing.problem.${key}`)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="pub-versus-card is-answer">
            <h3>{t('landing.problem.solutionTitle')}</h3>
            <ul>
              {SOLUTIONS.map((key) => (
                <li key={key}>
                  <Icon name="check" size="sm" />
                  <span>{t(`landing.problem.${key}`)}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

/** Built on Google Cloud: the services as an isometric stack that separates as it arrives. */
function CloudSection() {
  const { t } = useTranslation('public')
  const cloudRef = useRef<HTMLDivElement>(null)
  const cloudView = useInViewAttr(cloudRef)

  return (
    <section className="pub-section pub-paper">
      <div className="pub-inner pub-split">
        <Reveal>
          <div className="pub-head">
            <p className="pub-eyebrow">{t('landing.cloud.eyebrow')}</p>
            <h2 className="pub-h2">{t('landing.cloud.title')}</h2>
            <p className="pub-lead">{t('landing.cloud.lead')}</p>
          </div>
          <ul className="pub-ticks">
            {CLOUD_ITEMS.map((item) => (
              <li key={item}>
                <Icon name="check" size="sm" />
                <span>{t(`landing.cloud.${item}`)}</span>
              </li>
            ))}
          </ul>
        </Reveal>
        <div ref={cloudRef} className="pub-cloud" {...cloudView}>
          <div className="pub-plates" aria-hidden="true">
            <div className="pub-plates-iso">
              {PLATES.map((svc) => (
                <span className="pub-plate" key={svc.key}>
                  <Icon name={svc.icon} />
                </span>
              ))}
            </div>
          </div>
          <ul className="pub-svc" aria-label={t('landing.cloudStack.title')}>
            {CLOUD_STACK.map((svc) => (
              <li key={svc.key}>
                <span className="ico">
                  <Icon name={svc.icon} />
                </span>
                <span>
                  <strong>{t(`landing.cloudStack.${svc.key}Name`)}</strong>
                  <span>{t(`landing.cloudStack.${svc.key}Role`)}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

/** The product's real screens, rising and lying flat as they scroll in. */
function ScreensSection() {
  const { t } = useTranslation('public')
  const screensRef = useRef<HTMLDivElement>(null)
  useScrollProgress(screensRef, { offset: ['start end', 'start 25%'] })

  return (
    <Lamp className="pub-section is-sheet">
      <div className="pub-inner">
        <Reveal className="pub-head">
          <p className="pub-eyebrow">{t('landing.flow.eyebrow')}</p>
          <h2 className="pub-h2">{t('landing.flow.title')}</h2>
          <p className="pub-lead">{t('landing.flow.lead')}</p>
        </Reveal>
        <div ref={screensRef} className="pub-screens">
          {SCREENS.map((shot) => (
            <figure className="pub-shot" key={shot.src}>
              <img src={shot.src} alt="" loading="lazy" width={1440} height={900} />
              <figcaption>{t(shot.caption)}</figcaption>
            </figure>
          ))}
        </div>
      </div>
    </Lamp>
  )
}

/** The five trust rules, flipping up into place in turn. */
function TrustRules() {
  const { t } = useTranslation('public')
  const ref = useRef<HTMLOListElement>(null)
  const inView = useInViewAttr(ref)

  return (
    <ol ref={ref} className="pub-rules" {...inView}>
      {TRUST_ITEMS.map((item) => (
        <li key={item}>
          <Icon name="shield-check" />
          <span>{t(`landing.trust.${item}`)}</span>
        </li>
      ))}
    </ol>
  )
}
