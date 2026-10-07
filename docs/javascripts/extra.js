function activateRevealAnimations() {
  const elements = document.querySelectorAll('.reveal');
  if (!elements.length) {
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    },
    {
      rootMargin: '0px 0px -8% 0px',
      threshold: 0.18,
    }
  );

  elements.forEach((el, index) => {
    el.style.transitionDelay = `${Math.min(index * 45, 280)}ms`;
    observer.observe(el);
  });
}

function isCoarsePointer() {
  return window.matchMedia('(hover: none), (pointer: coarse)').matches;
}

function toggleSkillCard(card, forceOpen) {
  const nextState = typeof forceOpen === 'boolean' ? forceOpen : !card.classList.contains('is-details-visible');
  card.classList.toggle('is-details-visible', nextState);
  card.setAttribute('aria-expanded', nextState ? 'true' : 'false');

  const backFace = card.querySelector('.cv-meter-face--back');
  if (backFace) {
    backFace.setAttribute('aria-hidden', nextState ? 'false' : 'true');
  }
}

function setPhotoZoom(photo, open) {
  photo.classList.toggle('is-zoomed', open);
  photo.setAttribute('aria-pressed', open ? 'true' : 'false');

  const preview = photo.querySelector('.cv-hero__photo-preview');
  if (preview) {
    preview.setAttribute('aria-hidden', open ? 'false' : 'true');
  }
}

function activateInteractiveCards() {
  const photo = document.querySelector('.cv-hero__photo');
  if (photo && !photo.dataset.cvBound) {
    photo.dataset.cvBound = 'true';
    photo.setAttribute('aria-pressed', 'false');
    setPhotoZoom(photo, false);

    photo.addEventListener('click', () => {
      const nextState = !photo.classList.contains('is-zoomed');
      setPhotoZoom(photo, nextState);
    });

    photo.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      event.preventDefault();
      const nextState = !photo.classList.contains('is-zoomed');
      setPhotoZoom(photo, nextState);
    });

    document.addEventListener('click', (event) => {
      if (!photo.classList.contains('is-zoomed')) {
        return;
      }
      if (photo.contains(event.target)) {
        return;
      }
      setPhotoZoom(photo, false);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        setPhotoZoom(photo, false);
      }
    });
  }

  const skillCards = document.querySelectorAll('.cv-meter-item--has-details');
  skillCards.forEach((card) => {
    if (card.dataset.cvBound) {
      return;
    }
    card.dataset.cvBound = 'true';
    card.setAttribute('aria-expanded', 'false');
    toggleSkillCard(card, false);

    card.addEventListener('click', () => {
      if (!isCoarsePointer()) {
        return;
      }
      toggleSkillCard(card);
    });

    card.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      event.preventDefault();
      toggleSkillCard(card);
    });

    card.addEventListener('blur', () => {
      if (isCoarsePointer()) {
        return;
      }
      toggleSkillCard(card, false);
    });
  });
}

if (typeof window.document$ !== 'undefined') {
  window.document$.subscribe(() => {
    activateRevealAnimations();
    activateInteractiveCards();
  });
} else {
  window.addEventListener('DOMContentLoaded', () => {
    activateRevealAnimations();
    activateInteractiveCards();
  });
}
