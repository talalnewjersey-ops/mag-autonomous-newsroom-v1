print('Post ID:', wp_post_id)
print('Img IDs:', media_ids)
print('Featured:', image_report.get('featured_media_id', 'none'))
print('Provider:', image_report.get('provider_used', 'none'))
print('Cost   : $' + str(round(openai_cost + img_cost, 4)))
print('Time   :', str(elapsed) + 's')


if passed >= 7 and critical_ok and results.get('word_count_5000plus') and results.get('images_generated'):
    print('STATUS : PUBLISHED (draft) - ALL GATES PASS')
elif passed >= 6 and critical_ok:
    print('STATUS : PARTIAL - REVIEW REQUIRED')
else:
    print('STATUS : FAIL')
print('=' * 60)


report = {
    'version': 'v2',
    'article_index': ARTICLE_INDEX,
    'topic': TOPIC,
    'market': MARKET,
    'category': 'Newcomers to the USA' if MARKET == 'usa' else 'Newcomers to Canada',
    'word_count': len(article_content.split()) if article_content else 0,
    'seo_score': seo_score,
    'eeat_score': eeat_score,
    'internal_links': internal_links,
    'checks': {n: v for n, v in checks},
    'score': str(passed) + '/' + str(total_checks),
    'critical_ok': critical_ok,
    'wp_post_id': wp_post_id,
    'images_generated': len(generated_images),
    'media_ids': media_ids,
    'featured_media_id': image_report.get('featured_media_id'),
    'image_provider': image_report.get('provider_used'),
    'yoast_configured': True if wp_post_id else False,
    'openai_cost_usd': round(openai_cost, 5),
    'total_cost_usd': round(openai_cost + img_cost, 5),
    'total_tokens': total_tokens,
    'elapsed_seconds': elapsed,
    'timestamp': datetime.utcnow().isoformat()
}


report_file = 'execution_report_' + ARTICLE_INDEX + '.json'
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2)
print('Report:', report_file)


# Exit code: fail if critical gates not met
if not critical_ok:
    sys.exit(1)
if not results.get('word_count_5000plus', False):
    sys.exit(1)

