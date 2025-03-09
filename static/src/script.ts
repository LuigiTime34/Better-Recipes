/**
 * Helper functions for the recipe selection interface
 */

function showHelp(): void {
  const overlay = document.getElementById('overlay') as HTMLElement;
  const helpModal = document.getElementById('helpModal') as HTMLElement;
  overlay.classList.add('show');
  helpModal.classList.add('show');
  // Add a fade-in animation class
  helpModal.classList.add('animate-fade-in');
}

function hideHelp(): void {
  const overlay = document.getElementById('overlay') as HTMLElement;
  const helpModal = document.getElementById('helpModal') as HTMLElement;
  overlay.classList.remove('show');
  helpModal.classList.remove('show');
  helpModal.classList.remove('animate-fade-in');
}

function toggleSelection(element: HTMLElement, optionId: string): void {
  element.classList.toggle('selected');
  const checkbox = element.querySelector('input[type="checkbox"]') as HTMLInputElement;
  checkbox.checked = !checkbox.checked;
  updateSelectedList();
}

function updateSelectedList(): void {
  const selectedList = document.getElementById('selected-list') as HTMLUListElement;
  selectedList.innerHTML = '';
  let count = 0;
  document.querySelectorAll('.grid-item.selected').forEach((item: Element) => {
    const li = document.createElement('li');
    li.textContent = item.getAttribute('data-name') || '';
    selectedList.appendChild(li);
    count++;
  });
  
  const countElement = document.getElementById('selected-items-count') as HTMLElement;
  const selectedCountElement = document.getElementById('selected-count') as HTMLElement;
  
  countElement.textContent = count.toString();
  selectedCountElement.textContent = 'Selected: ' + count;
}

// Initialize the application when DOM is fully loaded
document.addEventListener('DOMContentLoaded', (): void => {
  // Set up hover preview for grid items
  document.querySelectorAll('.grid-item').forEach((item: Element) => {
    const gridItem = item as HTMLElement;
    const checkbox = gridItem.querySelector('input[type="checkbox"]') as HTMLInputElement;
    
    if (checkbox.checked) {
      gridItem.classList.add('selected');
    }

    gridItem.addEventListener('mouseenter', (): void => {
      const description = gridItem.getAttribute('data-description') || '';
      const imageSrc = gridItem.getAttribute('data-image') || '';
      
      const previewDescription = document.getElementById('preview-description') as HTMLElement;
      const previewImg = document.getElementById('preview-image') as HTMLImageElement;
      
      previewDescription.textContent = description;
      previewImg.src = imageSrc;
      previewImg.style.display = 'block';
    });
  });

  // Search functionality
  const searchBar = document.getElementById('searchBar') as HTMLInputElement;
  searchBar.addEventListener('keyup', function(): void {
    const query = this.value.toLowerCase();
    document.querySelectorAll('.grid-item').forEach((item: Element) => {
      const gridItem = item as HTMLElement;
      const name = gridItem.getAttribute('data-name')?.toLowerCase() || '';
      
      if (name.includes(query)) {
        gridItem.style.display = 'block';
      } else {
        gridItem.style.display = 'none';
      }
    });
  });

  // Initialize details elements with animation
  setupDetailsAnimations();
  
  // Initialize form submission
  setupFormSubmission();
  
  // Initial update of the selected list
  updateSelectedList();
});

function selectAll(): void {
  document.querySelectorAll('.grid-item').forEach((item: Element) => {
    const gridItem = item as HTMLElement;
    gridItem.classList.add('selected');
    const checkbox = gridItem.querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.checked = true;
  });
  updateSelectedList();
}

function deselectAll(): void {
  document.querySelectorAll('.grid-item').forEach((item: Element) => {
    const gridItem = item as HTMLElement;
    gridItem.classList.remove('selected');
    const checkbox = gridItem.querySelector('input[type="checkbox"]') as HTMLInputElement;
    checkbox.checked = false;
  });
  updateSelectedList();
}

// Animate <details> opening and closing
function setupDetailsAnimations(): void {
  document.querySelectorAll("details").forEach((detail: Element) => {
    const detailsElement = detail as HTMLDetailsElement;
    const summary = detailsElement.querySelector("summary") as HTMLElement;
    
    summary.addEventListener("click", (event: Event) => {
      event.preventDefault();
      const isOpen = detailsElement.hasAttribute("open");
      const summaryHeight = summary.offsetHeight;
      
      if (isOpen) {
        const fullHeight = detailsElement.scrollHeight;
        detailsElement.style.height = fullHeight + "px";
        detailsElement.style.transition = "height 0.3s ease";
        
        requestAnimationFrame(() => {
          detailsElement.style.height = summaryHeight + "px";
        });
        
        detailsElement.addEventListener("transitionend", function handler() {
          detailsElement.removeAttribute("open");
          detailsElement.style.height = "";
          detailsElement.style.transition = "";
          detailsElement.removeEventListener("transitionend", handler);
        });
      } else {
        detailsElement.setAttribute("open", "");
        const fullHeight = detailsElement.scrollHeight;
        detailsElement.style.height = summaryHeight + "px";
        detailsElement.style.transition = "height 0.3s ease";
        
        requestAnimationFrame(() => {
          detailsElement.style.height = fullHeight + "px";
        });
        
        detailsElement.addEventListener("transitionend", function handler() {
          detailsElement.style.height = "";
          detailsElement.style.transition = "";
          detailsElement.removeEventListener("transitionend", handler);
        });
      }
    });
  });
}

// Create and setup progress ring SVG
function createProgressRing(button: HTMLElement): SVGSVGElement {
  const ring = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  ring.setAttribute('class', 'progress-ring');

  // Get button dimensions
  const buttonRect = button.getBoundingClientRect();
  const size = Math.min(buttonRect.height, buttonRect.width);
  const strokeWidth = 2;
  const radius = (size / 2) - strokeWidth;
  const circumference = radius * 2 * Math.PI;

  // Set viewBox and size
  ring.setAttribute('width', size.toString());
  ring.setAttribute('height', size.toString());
  ring.setAttribute('viewBox', `0 0 ${size} ${size}`);

  ring.innerHTML = `
    <circle r="${radius}" cx="${size/2}" cy="${size/2}"
            stroke-dasharray="${circumference} ${circumference}"
            stroke-dashoffset="${circumference}" />
  `;

  return ring;
}

// Setup form submission with progress animation
function setupFormSubmission(): void {
  const form = document.getElementById('create-form') as HTMLFormElement;
  if (!form) return;
  
  form.onsubmit = async function(e: Event) {
    e.preventDefault();

    const button = document.querySelector('.download-button') as HTMLButtonElement;
    const spinner = document.createElement('div');
    spinner.className = 'spinner';

    // Create and add progress ring if it doesn't exist
    let ring = button.querySelector('.progress-ring') as SVGSVGElement;
    if (!ring) {
      ring = createProgressRing(button);
      button.appendChild(ring);
    }

    // Store original button text
    const originalText = button.textContent || '';

    try {
      // Start animation
      button.disabled = true;
      button.classList.add('loading');
      button.appendChild(spinner);
      spinner.style.display = 'block';
      button.textContent = 'Generating...';

      // Animate progress ring
      const circle = ring.querySelector('circle') as SVGCircleElement;
      const radius = parseFloat(circle.getAttribute('r') || '0');
      const circumference = radius * 2 * Math.PI;
      let progress = 0;

      const progressInterval = setInterval(() => {
        progress += 2;
        const offset = circumference - (progress / 100) * circumference;
        circle.style.strokeDashoffset = offset.toString();
        if (progress >= 100) clearInterval(progressInterval);
      }, 20);

      // Submit form
      const formData = new FormData(form);
      const response = await fetch(window.location.href, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Download failed');

      // Success animation
      clearInterval(progressInterval);
      circle.style.strokeDashoffset = '0';
      button.classList.remove('loading');
      button.classList.add('success');
      button.textContent = 'Download Starting...';

      // Handle the blob response
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      const contentDisposition = response.headers.get('content-disposition');
      a.download = contentDisposition?.split('filename=')[1] || 'datapack.zip';
      
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
}
