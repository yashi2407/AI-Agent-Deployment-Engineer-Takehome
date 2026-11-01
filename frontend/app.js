'use strict';
const $ = (id) => document.getElementById(id);
const form = $('story-form');
let currentStory = null;
let currentRequest = null;
let busy = false;
const feedbackForm = $('feedback-form');
let downloadUrl = null;
function updateCount() { $('count').textContent = `${$('prompt').value.length} / 1200`; }
$('prompt').addEventListener('input', updateCount);
document.querySelectorAll('[data-prompt]').forEach(button => {
  button.addEventListener('click', () => {
    $('prompt').value = button.dataset.prompt;
    updateCount();
    $('prompt').focus();
  });
});
async function requestStory(payload, isFeedback = false) {
  if (busy) return;
  busy = true;
  if (!isFeedback) $('result').hidden = true;
  $('error').hidden = true;
  $('loading').hidden = false;
  form.setAttribute('aria-busy', 'true');
  feedbackForm.setAttribute('aria-busy', 'true');
  document.querySelectorAll('form button, form select, form textarea').forEach(el => el.disabled = true);
  $('button-label').textContent = 'Weaving your story…';
  $('revise').textContent = isFeedback ? 'Weaving in your ideas…' : 'Rewrite with my feedback ✧';
  if (isFeedback) $('loading').scrollIntoView({behavior: 'smooth', block: 'center'});
  try {
    const response = await fetch('/api/stories', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your story idea and try again.');
    currentStory = data;
    currentRequest = {prompt: payload.prompt, age: payload.age, length: payload.length};
    $('feedback').value = '';
    $('story-title').textContent = data.title;
    $('story-meta').textContent = `For age ${data.age} · About ${data.reading_minutes} min · ${data.word_count} words`;
    $('story-text').replaceChildren(...data.story.split(/\n+/).filter(p => p.trim()).map(text => {
      const p = document.createElement('p'); p.textContent = text; return p;
    }));
    const review = data.reviews[data.reviews.length - 1];
    const labels = {age_fit:'Age fit', story_arc:'Story arc', warmth:'Warmth', bedtime:'Bedtime calm', request_fit:'Your idea'};
    $('review-scores').className = 'scores';
    $('review-scores').replaceChildren(...Object.entries(review.scores).map(([key, value]) => {
      const span = document.createElement('span'); span.className = 'score';
      span.textContent = `${labels[key] || key}: ${value}/5`; return span;
    }));
    $('review-note').textContent = `Reviewed ${data.reviews.length} time(s), with ${data.revisions} revision(s). ${review.feedback}`;
    $('result').hidden = false;
    $('result').focus({preventScroll: true});
    $('result').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {
    $('error').textContent = error instanceof TypeError ? 'We could not reach the storyteller. Check your connection and try again.' : error.message;
    $('error').hidden = false;
  } finally {
    $('loading').hidden = true;
    form.removeAttribute('aria-busy');
    feedbackForm.removeAttribute('aria-busy');
    document.querySelectorAll('form button, form select, form textarea').forEach(el => el.disabled = false);
    $('revise').textContent = 'Rewrite with my feedback ✧';
    busy = false;
    $('button-label').textContent = 'Make a little magic';
  }
}
form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  requestStory({prompt: $('prompt').value.trim(), age: Number($('age').value), length: $('length').value});
});
feedbackForm.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!feedbackForm.reportValidity() || !currentStory || !currentRequest) return;
  requestStory({...currentRequest, feedback: $('feedback').value.trim(),
    previous_story: {title: currentStory.title, story: currentStory.story}}, true);
});
$('again').addEventListener('click', () => {
  form.scrollIntoView({behavior:'smooth', block:'center'});
  $('prompt').focus({preventScroll:true});
});
$('download').addEventListener('click', () => {
  if (!currentStory) return;
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = URL.createObjectURL(new Blob([`${currentStory.title}\n\n${currentStory.story}\n`], {type:'text/plain;charset=utf-8'}));
  const a = document.createElement('a'); a.href = downloadUrl; a.download = 'moonbeam-story.txt'; a.click();
});
