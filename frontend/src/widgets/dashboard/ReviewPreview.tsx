/** The period's first open review items, in the queue's order (spec 010, T010-04a, AC-010-1). */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { ReviewItem } from '../../entities/review'
import { KIND_ICON } from '../../features/review'
import { formatMonth } from '../../shared/lib/formatDate'
import { Icon } from '../../shared/ui'

const TILE: Record<string, string> = { POSSIBLE_DUPLICATE: 'dup', PROPOSED_MATCH: 'match' }

export function ReviewPreview({ items }: { items: ReviewItem[] }) {
  const { t } = useTranslation(['dashboard', 'review'])
  return (
    <section className="panel" aria-labelledby="dash-review-h">
      <div className="panel-head">
        <h2 id="dash-review-h">{t('dashboard:review')}</h2>
        <Link className="link" to="/review">
          {t('dashboard:allReview')}
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="muted small p-4">{t('dashboard:nothingToReview')}</p>
      ) : (
        <ul className="alert-list">
          {items.map((item) => (
            <li key={item.itemId}>
              <Link to={`/review/${item.itemId}`}>
                <span className={`kind ${TILE[item.kind] ?? 'doc'}`}>
                  <Icon name={KIND_ICON[item.kind] ?? 'inbox'} size="sm" />
                </span>
                <span>
                  <p className="a-t">{item.title}</p>
                  <p className="a-s">
                    {t(`review:kinds.${item.kind}`)}
                    {item.month ? `, ${formatMonth(item.month)}` : ''}
                  </p>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
