/* global bootstrap: false */
const initializeTooltips = () => {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
};


// Item information from password list
const setupResourceClickHandlers = () => {
    const resourceItems = document.querySelectorAll('.list-resource-item:not(.d-none)');
    const resourceName = document.querySelector('.resource-name');
    const resourceUsername = document.querySelector('.resource-username');
    const resourceEmail = document.querySelector('.resource-email');
    const resourcePassword = document.querySelector('.resource-password');
    const resourceURL = document.querySelector('.resource-url');
    const resourceCreationDate = document.querySelector('.resource-creation-date');
    const resourceModifiedDate = document.querySelector('.resource-modified-date');
    const resourceID = document.querySelector('.resource-id-val');

    const setActiveItem = (clickedItem) => {
        resourceItems.forEach(item => {
            item.classList.remove('list-group-item-active')
            selectedItemId = item.getAttribute('data-id');
        });

        clickedItem.classList.add('list-group-item-active');
        selectedItemId = clickedItem.getAttribute('data-id');
    }

    const loadResourceDetails = (resourceId) => {
        const resource = resources[resourceId];
        if (resource) {
            resourceName.value = `${resource.name}`;
            resourceUsername.value = `${resource.username}`;
            resourceEmail.value = `${resource.email}`;
            resourcePassword.value = `${resource.password}`;
            resourceURL.value = `${resource.resource_url || 'N/A'}`;
            resourceCreationDate.value = `${resource.resource_creation_date}`;
            resourceModifiedDate.value = `${resource.pass_last_modified_date}`;
            resourceID.value = resourceId;
        }
    };

    resourceItems.forEach(item => {
        item.addEventListener('click', (event) => {
            event.preventDefault();

            const resourceId = item.getAttribute('data-id');
            setActiveItem(item);
            loadResourceDetails(resourceId);

            const urlPath = window.location.pathname;
            const vaultIdMatch = urlPath.match(/\/password-list\/vault\/(\d+)/);
            const vaultId = vaultIdMatch ? vaultIdMatch[1] : null;

            const newUrl = vaultId
                ? `/password-list/vault/${vaultId}/resource/${resourceId}`
                : `/password-list/resource/${resourceId}`;
            window.history.pushState({ resourceId }, '', newUrl);
        });
    });

    let selectedResourceId = null;
    if (selectedResourceId) {
        const selectedItem = document.querySelector(
            `.list-resource-item[data-id="${selectedResourceId}"]`
        );
        if (selectedItem) {
            setActiveItem(selectedItem);
            loadResourceDetails(selectedResourceId);
        }
    } else if (resourceItems.length > 0) {
        // Select the first item if no selectedResourceId is provided
        const firstResource = resourceItems[0];
        firstResource.click();
    }

    // Allows for forward & backtracking through a list of resources
    window.addEventListener('popstate', (event) => {
        const resourceId = event.state ? event.state.resourceId : null;
        if (resourceId) {
            loadResourceDetails(resourceId);

            // Set the active item visually
            const activeItem = document.querySelector(
                `.list-resource-item[data-id="${resourceId}"]`
            );
            if (activeItem) {
                setActiveItem(activeItem);
            }
        }
    });
};


const editResourcesInformation = () => {
    const editButton = document.querySelector('.edit-button');
    const saveButton = document.querySelector('.save-button');

    if (editButton) {
        editButton.addEventListener('click', function () {
            document.querySelectorAll('.form-control').forEach(input => {
                if (!input.classList.contains('resource-exception-date')) {
                    input.disabled = false
                }
            });
            document.querySelector('.edit-button').style.display = 'none';
            document.querySelector('.save-button').style.display = 'inline-block';
        });
    }

    if (saveButton) {
        document.querySelector('.save-button').addEventListener('click', function () {
            const form = document.querySelector('.resource-form');
            const data = new FormData(form);

            form.submit();
        });
    }
};


const toggleListVisibility = () => {
    document.querySelectorAll('.list-resource-stats-item').forEach(button => {
        button.addEventListener('click', () => {
            const targetId = button.getAttribute('data-target');
            if (targetId) {
                // Hide all buttons
                document.querySelectorAll('.list-resource-stats-item').forEach(btn => {
                    btn.classList.add('d-none');
                });

                // Show the associated list
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    targetElement.classList.remove('d-none');
                } else {
                    console.error(`Element with ID "${targetId}" not found.`);
                }
            }
        });
    });

    // Event delegation for "Back" buttons
    document.querySelectorAll('.back-to-main').forEach(backButton => {
        backButton.addEventListener('click', () => {
            const targetId = backButton.getAttribute('data-target');
            if (targetId) {
                // Show the button
                document.querySelectorAll('.list-resource-stats-item').forEach(btn => {
                    btn.classList.remove('d-none');
                });
                // Hide the associated list
                document.getElementById(targetId).classList.add('d-none');
            }
        });
    });
};


const searchResource = () => {
    const searchInput = document.querySelector('.search-resource-input');
    const resources = document.querySelectorAll('.resource-to-search');

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase();

            resources.forEach(resource => {
                const resourceName = resource.querySelector('.resource-to-search-name')
                    .textContent.toLowerCase();

                if (resourceName.includes(query)) {
                    resource.classList.remove('d-none');
                    resource.classList.add('d-flex');
                    setupResourceClickHandlers();
                } else {
                    resource.classList.add('d-none');
                    resource.classList.remove('d-flex');
                    setupResourceClickHandlers();
                }
            });
        });
    }
};


const clearSearchInput = () => {
    const clearButton = document.getElementById('clear-button');

    if (clearButton) {
        const searchInput = document.querySelector('.search-resource-input');
        clearButton.addEventListener('click', (e) => {
            e.preventDefault();

            searchInput.value = '';

            const inputEvent = new Event('input');
            searchInput.dispatchEvent(inputEvent);
        })
    }
};


// Saves the input text after the page reload
const saveInputText = () => {
    const inputField = document.querySelector('.search-resource-input');
    const clearButton = document.getElementById('clear-button');

    // Retrieve and set the saved input value
    const savedValue = localStorage.getItem('searchInput');
    if (savedValue) {
        inputField.value = savedValue;

        // Highlight the text
        inputField.focus();
        inputField.select();

        const inputEvent = new Event('input');
        inputField.dispatchEvent(inputEvent);
    }

    window.addEventListener('beforeunload', () => {
        localStorage.setItem('searchInput', inputField.value);
    });

    clearButton.addEventListener('click', () => {
        localStorage.removeItem('searchInput');
    })
};


const togglePasswordVisibility = () => {
   const togglePasswordButtons = document.querySelectorAll('.toggle-password-btn');

    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', () => {
            const passwordInput = button.previousElementSibling;
            const icon = button.querySelector('i');

            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });
}


// Automatically removes flash messages after 3 seconds
const removeFlashMessages = () => {
    setTimeout(() => {
        const flashMessages = document.getElementById('flash-messages');
        if (flashMessages) {
            flashMessages.remove();
        }
    }, 3000);
}


document.addEventListener('DOMContentLoaded', () => {
    initializeTooltips();
    setupResourceClickHandlers();
    editResourcesInformation();
    removeFlashMessages();
    toggleListVisibility();
    searchResource();
    clearSearchInput();
    saveInputText();
    togglePasswordVisibility();
});