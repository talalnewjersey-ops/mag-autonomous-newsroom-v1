"""
AGENT 21 - STAGE 0 PRE-VALIDATOR
NEXUS-14 Enterprise v9.0

Responsabilité: Vérifier AVANT la génération si le sujet est viable
- Vérifier existence du sujet
- Vérifier existence du slug
- Détecter cannibalisation potentielle
- Évaluer similarité avec articles existants
"""

import json
import hashlib
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from anthropic import Anthropic
import os

class Stage0PreValidator:
      """Pre-validation avant génération d'article"""

    def __init__(self):
              self.client = Anthropic()
              self.published_articles = self.load_published_articles()
              self.conversation_history = []

    def load_published_articles(self) -> List[Dict]:
              """Charger la liste des articles publiés"""
              # TODO: Connecter à WordPress/Database
              return []

    def check_subject_exists(self, subject: str) -> Tuple[bool, Optional[str]]:
              """Vérifier si le sujet existe déjà"""
              for article in self.published_articles:
                            if article['title'].lower() == subject.lower():
                                              return True, article['id']
                                      return False, None

          def check_slug_exists(self, slug: str) -> Tuple[bool, Optional[str]]:
                    """Vérifier si le slug existe déjà"""
                    for article in self.published_articles:
                                  if article['slug'].lower() == slug.lower():
                                                    return True, article['id']
                                            return False, None

                def generate_slug(self, subject: str) -> str:
                          """Générer un slug à partir du sujet"""
                          return subject.lower().replace(' ', '-').replace('/', '-')

    def calculate_similarity(self, subject: str, existing_subject: str) -> float:
              """Calculer la similarité entre deux sujets (0-1)"""
              words_new = set(subject.lower().split())
              words_existing = set(existing_subject.lower().split())

        if not words_new or not words_existing:
                      return 0.0

        intersection = len(words_new & words_existing)
        union = len(words_new | words_existing)
        return intersection / union if union > 0 else 0.0

    def detect_cannibalization_risk(self, subject: str, threshold: float = 0.6) -> Tuple[bool, List[Dict]]:
              """Détecter le risque de cannibalisation"""
              similar_articles = []

        for article in self.published_articles:
                      similarity = self.calculate_similarity(subject, article['title'])
                      if similarity >= threshold:
                                        similar_articles.append({
                                                              'title': article['title'],
                                                              'similarity': similarity,
                                                              'url': article.get('url', 'N/A')
                                        })

                  return len(similar_articles) > 0, similar_articles

    def validate_subject(self, subject: str) -> Dict:
              """Validation complète du sujet"""
              slug = self.generate_slug(subject)

        # Vérification 1: Le sujet existe-t-il?
              exists, article_id = self.check_subject_exists(subject)
              if exists:
                            return {
                                              'valid': False,
                                              'reason': 'SUBJECT_EXISTS',
                                              'message': f'Ce sujet existe déjà (ID: {article_id})',
                                              'action': 'choose_another_subject'
                            }

              # Vérification 2: Le slug existe-t-il?
              slug_exists, article_id = self.check_slug_exists(slug)
              if slug_exists:
                            return {
                                              'valid': False,
                                              'reason': 'SLUG_EXISTS',
                                              'message': f'Ce slug existe déjà (ID: {article_id})',
                                              'action': 'choose_another_subject'
                            }

              # Vérification 3: Risque de cannibalisation?
              cannibalization, similar_articles = self.detect_cannibalization_risk(subject)
        if cannibalization:
                      return {
                                        'valid': False,
                                        'reason': 'HIGH_CANNIBALIZATION_RISK',
                                        'message': f'Risque élevé de cannibalisation avec {len(similar_articles)} articles',
                                        'similar_articles': similar_articles,
                                        'action': 'choose_different_angle'
                      }

        # Tous les checks passent
        return {
                      'valid': True,
                      'subject': subject,
                      'slug': slug,
                      'checks_passed': ['subject_unique', 'slug_unique', 'no_cannibalization'],
                      'message': 'Sujet validé - Prêt pour Editorial Brief',
                      'action': 'proceed_to_editorial_brief'
        }

    def suggest_alternative_subject(self, original_subject: str) -> str:
              """Utiliser Claude pour suggérer un sujet alternatif"""
              self.conversation_history = []

        prompt = f"""Tu es un expert éditorial SEO pour un site finance/immigration.

                Le sujet '{original_subject}' ne peut pas être utilisé.

                Suggère un sujet UNIQUE et DIFFÉRENT qui:
                1. N'existe pas encore sur le site
                2. Apporte une vraie valeur ajoutée
                3. Reste dans notre niche (finance, immigration, taxes, assurance, crédit)
                4. Évite la cannibalisation avec les articles existants

                Réponds directement avec le sujet proposé, sans explication."""

        self.conversation_history.append({
                      "role": "user",
                      "content": prompt
        })

        response = self.client.messages.create(
                      model="claude-3-5-sonnet-20241022",
                      max_tokens=200,
                      messages=self.conversation_history
        )

        suggested_subject = response.content[0].text.strip()
        self.conversation_history.append({
                      "role": "assistant",
                      "content": suggested_subject
        })

        return suggested_subject

    def process_batch_subjects(self, subjects: List[str]) -> Dict:
              """Traiter un batch de sujets et identifier les sujets valides"""
              results = {
                  'timestamp': datetime.now().isoformat(),
                  'processed': 0,
                  'valid_subjects': [],
                  'rejected_subjects': [],
                  'alternatives_suggested': []
              }

        for subject in subjects:
                      validation = self.validate_subject(subject)
                      results['processed'] += 1

            if validation['valid']:
                              results['valid_subjects'].append({
                                                    'subject': subject,
                                                    'slug': validation['slug']
                              })
else:
                  results['rejected_subjects'].append({
                                        'subject': subject,
                                        'reason': validation['reason'],
                                        'message': validation['message']
                  })

                # Suggérer une alternative
                  alternative = self.suggest_alternative_subject(subject)
                results['alternatives_suggested'].append({
                                      'rejected': subject,
                                      'alternative': alternative
                })

        return results


def main():
      """Test du Stage 0 Pre-Validator"""
      validator = Stage0PreValidator()

    # Test subjects
      test_subjects = [
                "How to Open a Bank Account in the USA",
                "Best Credit Cards for Immigration",
                "Tax Deductions for Self-Employed Freelancers"
      ]

    print("="*60)
    print("STAGE 0 - PRE-VALIDATION TEST")
    print("="*60)

    for subject in test_subjects:
              print(f"\n📋 Validating: {subject}")
              result = validator.validate_subject(subject)
              print(json.dumps(result, indent=2))

    # Test batch processing
    print("\n" + "="*60)
    print("BATCH PROCESSING TEST")
    print("="*60)

    batch_results = validator.process_batch_subjects(test_subjects)
    print(json.dumps(batch_results, indent=2))


if __name__ == "__main__":
      main()
  
