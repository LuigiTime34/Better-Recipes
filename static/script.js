
function showHelp() {
    const overlay = document.getElementById('overlay');
    const helpModal = document.getElementById('helpModal');
    overlay.classList.add('show');
    helpModal.classList.add('show');
    // Add a fade-in animation class
    helpModal.classList.add('animate-fade-in');
  }

  function hideHelp() {
    document.getElementById('overlay').classList.remove('show');
    document.getElementById('helpModal').classList.remove('show');
    document.getElementById('helpModal').classList.remove('animate-fade-in');
  }

  function toggleSelection(element, optionId) {
    element.classList.toggle('selected');
    const checkbox = element.querySelector('input[type="checkbox"]');
    checkbox.checked = !checkbox.checked;
    updateSelectedList();
  }

  function updateSelectedList() {
    const selectedList = document.getElementById('selected-list');
    selectedList.innerHTML = '';
    let count = 0;
    document.querySelectorAll('.grid-item.selected').forEach(item => {
      const li = document.createElement('li');
      li.textContent = item.getAttribute('data-name');
      selectedList.appendChild(li);
      count++;
    });
    document.getElementById('selected-items-count').textContent = count;
    document.getElementById('selected-count').textContent = 'Selected: ' + count;
  }

  // Set up hover preview for grid items.
  document.querySelectorAll('.grid-item').forEach(function(item) {
    if (item.querySelector('input[type="checkbox"]').checked) {
      item.classList.add('selected');
    }

    item.addEventListener('mouseenter', function() {
      const description = item.getAttribute('data-description');
      const imageSrc = item.getAttribute('data-image');
      document.getElementById('preview-description').textContent = description;
      const previewImg = document.getElementById('preview-image');
      previewImg.src = imageSrc;
      previewImg.style.display = 'block';
    });
  });

  // Search functionality
  document.getElementById('searchBar').addEventListener('keyup', function() {
    const query = this.value.toLowerCase();
    document.querySelectorAll('.grid-item').forEach(item => {
      const name = item.getAttribute('data-name').toLowerCase();
      if (name.includes(query)) {
        item.style.display = 'block';
      } else {
        item.style.display = 'none';
      }
    });
  });

  function selectAll() {
    document.querySelectorAll('.grid-item').forEach(item => {
      item.classList.add('selected');
      item.querySelector('input[type="checkbox"]').checked = true;
    });
    updateSelectedList();
  }

  function deselectAll() {
    document.querySelectorAll('.grid-item').forEach(item => {
      item.classList.remove('selected');
      item.querySelector('input[type="checkbox"]').checked = false;
    });
    updateSelectedList();
  }

  // Animate <details> opening and closing
  document.querySelectorAll("details").forEach(detail => {
    const summary = detail.querySelector("summary");
    summary.addEventListener("click", (event) => {
      event.preventDefault();
      const isOpen = detail.hasAttribute("open");
      const summaryHeight = summary.offsetHeight;
      if (isOpen) {
        const fullHeight = detail.scrollHeight;
        detail.style.height = fullHeight + "px";
        detail.style.transition = "height 0.3s ease";
        requestAnimationFrame(() => {
          detail.style.height = summaryHeight + "px";
        });
        detail.addEventListener("transitionend", function handler() {
          detail.removeAttribute("open");
          detail.style.height = "";
          detail.style.transition = "";
          detail.removeEventListener("transitionend", handler);
        });
      } else {
        detail.setAttribute("open", "");
        const fullHeight = detail.scrollHeight;
        detail.style.height = summaryHeight + "px";
        detail.style.transition = "height 0.3s ease";
        requestAnimationFrame(() => {
          detail.style.height = fullHeight + "px";
        });
        detail.addEventListener("transitionend", function handler() {
          detail.style.height = "";
          detail.style.transition = "";
          detail.removeEventListener("transitionend", handler);
        });
      }
    });
  });

  updateSelectedList();

    // Create and setup progress ring SVG
  function createProgressRing(button) {
    const ring = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    ring.setAttribute('class', 'progress-ring');

    // Get button dimensions
    const buttonRect = button.getBoundingClientRect();
    const size = Math.min(buttonRect.height, buttonRect.width);
    const strokeWidth = 2;
    const radius = (size / 2) - strokeWidth;
    const circumference = radius * 2 * Math.PI;

    // Set viewBox and size
    ring.setAttribute('width', size);
    ring.setAttribute('height', size);
    ring.setAttribute('viewBox', `0 0 ${size} ${size}`);

    ring.innerHTML = `
      <circle r="${radius}" cx="${size/2}" cy="${size/2}"
              stroke-dasharray="${circumference} ${circumference}"
              stroke-dashoffset="${circumference}" />
    `;

    return ring;
  }

  // Update the create form submission handler
  document.getElementById('create-form').onsubmit = async function(e) {
    e.preventDefault();

    const button = document.querySelector('.download-button');
    const spinner = document.createElement('div');
    spinner.className = 'spinner';

    // Create and add progress ring if it doesn't exist
    let ring = button.querySelector('.progress-ring');
    if (!ring) {
      ring = createProgressRing(button);
      button.appendChild(ring);
    }

    try {
      // Start animation
      button.disabled = true;
      button.classList.add('loading');
      button.appendChild(spinner);
      spinner.style.display = 'block';
      const originalText = button.textContent;
      button.textContent = 'Generating...';

      // Animate progress ring
      const circle = ring.querySelector('circle');
      const radius = parseFloat(circle.getAttribute('r'));
      const circumference = radius * 2 * Math.PI;
      let progress = 0;

      const progressInterval = setInterval(() => {
        progress += 2;
        const offset = circumference - (progress / 100) * circumference;
        circle.style.strokeDashoffset = offset;
        if (progress >= 100) clearInterval(progressInterval);
      }, 20);

      // Submit form
      const formData = new FormData(this);
      const response = await fetch(window.location.href, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Download failed');

      // Success animation
      clearInterval(progressInterval);
      circle.style.strokeDashoffset = 0;
      button.classList.remove('loading');
      button.classList.add('success');
      button.textContent = 'Download Starting...';

      // Handle the blob response
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.headers.get('content-disposition')?.split('filename=')[1] || 'datapack.zip';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Reset button after short delay
      setTimeout(() => {
        button.disabled = false;
        button.classList.remove('success');
        button.textContent = originalText;
        spinner.style.display = 'none';
        if (ring) ring.remove();
      }, 1000);

    } catch (error) {
      // Error animation
      button.classList.remove('loading');
      button.classList.add('error');
      button.textContent = 'Error! Try Again';

      setTimeout(() => {
        button.disabled = false;
        button.classList.remove('error');
        button.textContent = originalText;
        spinner.style.display = 'none';
        if (ring) ring.remove();
      }, 1500);
    }
  };